"""Opaque keyset (seek) cursor pagination for list endpoints (SDLC 09 §4 — ``Paginated<T>``).

List endpoints return ``{items, next_cursor}``. The cursor is an opaque,
base64-encoded token so callers treat it as a token, never an index. Internally it
is a **keyset** (seek) cursor: it encodes the ordering-field values of the last row
on the page, and the next page is fetched with a ``WHERE (…) ▷ cursor`` seek rather
than an ``OFFSET``. That makes deep pages O(1) (the database skips no rows) and
keeps a moving list — rows inserted or removed between requests — free of the
duplicate/skip artifacts an offset window suffers: the walk is anchored to the last
row seen, not to a positional offset that shifts when the head of the list moves.

Wire contract (unchanged from the previous offset implementation): the cursor stays
an opaque token — its format was always a server-internal detail, so this swap is
seamless. ``paginate(queryset, *, cursor, limit) -> (items, next_cursor)``,
``next_cursor`` is ``None`` on the final page, and any malformed or older-format
(base64 offset) cursor falls back to "start from the beginning" exactly as before.

The ordering is read from the queryset's own ``order_by`` (or the model's
``Meta.ordering``), so any deterministic ordering a caller sets — ``("-created_at",
"id")``, ``("handle",)``, ascending or descending, single or compound — is
supported without the caller changing anything. The caller MUST pass a deterministic
ordering (every current caller does); if none is present a stable ``pk`` ordering is
imposed so the seek is always well-defined.
"""

from __future__ import annotations

import base64
import binascii
import json
import uuid
from datetime import date, datetime
from typing import Any

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db.models import Field, Model, Q, QuerySet

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def clamp_limit(limit: int | None) -> int:
    """Bound a client-supplied page size to ``[1, MAX_LIMIT]`` (default when None)."""
    if limit is None:
        return DEFAULT_LIMIT
    return max(1, min(limit, MAX_LIMIT))


def _ordering_of(queryset: QuerySet[Any]) -> list[tuple[str, bool]]:
    """Extract the ordering as ``[(field_name, descending), …]`` from ``queryset``.

    Reads the queryset's explicit ``order_by`` first, then the model's
    ``Meta.ordering``. Each entry is a plain field name with an optional leading
    ``-`` (descending); ``pk`` is resolved to the concrete primary-key field name so
    the value can be read off a row and coerced back. A non-string ordering
    expression (``F()`` / ``OrderBy``) cannot drive a seek, so the extraction returns
    empty — the caller then imposes a deterministic ``pk`` fallback.
    """
    model = queryset.model
    raw: list[Any] = list(queryset.query.order_by)
    if not raw:
        raw = [entry for entry in (model._meta.ordering or []) if isinstance(entry, str)]
    fields: list[tuple[str, bool]] = []
    for entry in raw:
        if not isinstance(entry, str):
            return []
        descending = entry.startswith("-")
        name = entry[1:] if descending else entry
        if name == "pk":
            pk = model._meta.pk
            if pk is None:
                return []
            name = pk.name
        fields.append((name, descending))
    return fields


def _encode_value(value: Any) -> Any:
    """Reduce one ordering value to a JSON-serialisable primitive for the cursor.

    datetime/date/UUID become their canonical string form; int/bool/str pass through
    natively. ``Field.to_python`` reverses this on decode, so the seek compares real
    typed values, not strings.
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (bool, int, str)):
        return value
    return str(value)


def _encode(last_item: Model, ordering: list[tuple[str, bool]]) -> str:
    """Encode the last row's ordering values as an opaque cursor token."""
    payload = [_encode_value(getattr(last_item, name)) for name, _ in ordering]
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode(
    cursor: str | None,
    model: type[Model],
    ordering: list[tuple[str, bool]],
) -> list[Any] | None:
    """Decode a cursor to typed ordering values, or ``None`` to start at the beginning.

    Returns ``None`` (→ start) for an empty, malformed, or older-format (base64
    offset) cursor, and for a cursor whose arity no longer matches the current
    ordering (a shipped ordering change) — so a stale token degrades to "first page"
    instead of erroring, preserving the pre-existing malformed-cursor behaviour. Each
    value is coerced back to its field type via ``Field.to_python`` so the seek
    comparison uses a real datetime/UUID/int rather than a raw string.
    """
    if not cursor:
        return None
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(decoded)
    except (ValueError, binascii.Error):
        return None
    if not isinstance(data, list) or len(data) != len(ordering):
        return None
    coerced: list[Any] = []
    for (name, _), raw in zip(ordering, data, strict=True):
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist:
            return None
        # A relation/GenericForeignKey has no ``to_python`` and can't be a scalar
        # sort key; a stale cursor pointing at one degrades to "start".
        if not isinstance(field, Field):
            return None
        try:
            coerced.append(field.to_python(raw))
        except (ValidationError, ValueError, TypeError):
            return None
    return coerced


def _seek_predicate(ordering: list[tuple[str, bool]], values: list[Any]) -> Q:
    """Build the lexicographic "row strictly after the cursor" filter.

    For ordering ``(f1, f2, …)`` with per-field direction, the next page is
    ``(f1 ▷ v1) OR (f1 = v1 AND f2 ▷ v2) OR …`` where ``▷`` is ``>`` for an ascending
    field and ``<`` for a descending one — the standard keyset seek. The compound
    (tie-broken) form is what keeps rows with an equal leading key (e.g. the same
    ``created_at``) from being duplicated or skipped across a page boundary.
    """
    combined = Q()
    for i, (name, descending) in enumerate(ordering):
        clause = Q()
        for j in range(i):
            prev_name, _ = ordering[j]
            clause &= Q(**{prev_name: values[j]})
        op = "lt" if descending else "gt"
        clause &= Q(**{f"{name}__{op}": values[i]})
        combined |= clause
    return combined


def paginate[M: Model](
    queryset: QuerySet[M], *, cursor: str | None, limit: int | None
) -> tuple[list[M], str | None]:
    """Return one page of ``queryset`` plus the cursor for the next page.

    Seeks past the cursor row (keyset), then fetches ``limit + 1`` rows to detect
    whether more remain without a second count query. The queryset must carry a
    deterministic ``order_by`` (or ``Meta.ordering``); if it carries none a stable
    ``pk`` ordering is imposed so the seek is well-defined. Deep pages are O(1): the
    seek predicate uses indexed comparisons instead of a growing ``OFFSET``.
    """
    size = clamp_limit(limit)
    ordering = _ordering_of(queryset)
    if not ordering:
        pk = queryset.model._meta.pk
        pk_name = pk.name if pk is not None else "id"
        queryset = queryset.order_by(pk_name)
        ordering = [(pk_name, False)]
    values = _decode(cursor, queryset.model, ordering)
    if values is not None:
        queryset = queryset.filter(_seek_predicate(ordering, values))
    window = list(queryset[: size + 1])
    has_more = len(window) > size
    items = window[:size]
    next_cursor = _encode(items[-1], ordering) if has_more and items else None
    return items, next_cursor
