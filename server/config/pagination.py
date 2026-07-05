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
``Meta.ordering``), so any ordering a caller sets over **concrete, non-null model
fields** — ``("-created_at", "id")``, ``("handle",)``, ascending or descending,
single or compound — is supported without the caller changing anything. A ``pk``
tiebreak is auto-appended when the ordering does not already carry the primary key,
so even a non-unique leading key (``("handle",)``) becomes a total order and the seek
can never skip or duplicate a tied row across a page boundary. An ordering key a seek
cannot drive — an annotation alias, a relation path (``foo__bar``), a nullable field
that is actually ``None``, or a non-string ``F()``/``OrderBy`` expression — degrades
safely: the cursor is dropped (the next page reads as the last, a malformed inbound
cursor starts from the beginning), never a 500. The caller MUST pass a deterministic
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

# Upper bound on an inbound cursor's character length, checked *before* any base64
# decode or JSON parse so an attacker can't hand us an arbitrarily large token to
# expand and walk. A legitimate cursor is a base64 JSON array of a handful of
# sort-key values (a datetime is ~32 chars, a UUID ~36) — tens of characters, and
# under a hundred even for a compound ordering. 512 leaves generous headroom for any
# real ordering while rejecting oversized payloads (e.g. a deeply nested-JSON bomb)
# outright; an over-length token degrades to "start from the beginning" like any
# other malformed cursor.
MAX_CURSOR_LEN = 512


def clamp_limit(limit: int | None) -> int:
    """Bound a client-supplied page size to ``[1, MAX_LIMIT]`` (default when None)."""
    if limit is None:
        return DEFAULT_LIMIT
    return max(1, min(limit, MAX_LIMIT))


def _ordering_of(queryset: QuerySet[Any]) -> list[tuple[str, bool]]:
    """Extract the seek ordering as ``[(field_name, descending), …]`` from ``queryset``.

    Reads the queryset's explicit ``order_by`` first, then the model's
    ``Meta.ordering``. Each entry must be a plain field name with an optional leading
    ``-`` (descending); ``pk`` resolves to the concrete primary-key field name. Both
    sources are treated symmetrically: a single non-string ordering expression
    (``F()`` / ``OrderBy``) in *either* one cannot drive a seek, so the whole
    extraction returns empty — the caller then imposes a deterministic ``pk``-only
    fallback rather than silently keeping a partial ordering the SQL would not seek by
    (which would desync the seek from the actual ``ORDER BY`` and skip rows).

    A ``pk`` tiebreak is appended unless the primary key is already among the keys, so
    a non-unique leading key (e.g. ``("created_at",)`` or ``("handle",)``) can never
    skip or duplicate a tied row across a page boundary: the final key is always unique.
    """
    model = queryset.model
    pk = model._meta.pk
    if pk is None:
        return []
    raw: list[Any] = list(queryset.query.order_by)
    if not raw:
        raw = list(model._meta.ordering or [])
    fields: list[tuple[str, bool]] = []
    for entry in raw:
        if not isinstance(entry, str):
            return []
        descending = entry.startswith("-")
        name = entry[1:] if descending else entry
        if name == "pk":
            name = pk.name
        fields.append((name, descending))
    # pk tiebreak: guarantee a unique final key so the seek is a total order and a
    # tied non-unique key cannot skip/duplicate a row at a page boundary.
    if pk.name not in {name for name, _ in fields}:
        fields.append((pk.name, False))
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


def _encode(last_item: Model, ordering: list[tuple[str, bool]]) -> str | None:
    """Encode the last row's ordering values as an opaque cursor token, or ``None``.

    Returns ``None`` (→ no next cursor; the page reads as the last) when a sort key
    cannot yield a usable seek value: a relation-path / annotation-alias key raises
    ``AttributeError`` on ``getattr``, and a nullable field can be ``None`` — neither
    can seat a ``> value`` seek, so the cursor is dropped instead of surfacing a 500
    or emitting a ``"None"`` token that would mis-seek on the next request. Concrete
    non-null values (int/str/datetime/date/UUID) encode normally.
    """
    payload: list[Any] = []
    for name, _ in ordering:
        try:
            value = getattr(last_item, name)
        except AttributeError:
            return None
        if value is None:
            return None
        payload.append(_encode_value(value))
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
    # Guard the size *before* decoding: reject an over-length token outright (see
    # ``MAX_CURSOR_LEN``) so a hostile caller can't force us to base64-decode and
    # JSON-parse a large payload.
    if len(cursor) > MAX_CURSOR_LEN:
        return None
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(decoded)
    # ``RecursionError`` guards a deeply nested-JSON bomb (base64 of ``[[[…]]]``),
    # which ``json.loads`` raises rather than a ``ValueError`` — an uncaught one
    # would surface as a 500 instead of the "start from the beginning" fallback.
    except (ValueError, binascii.Error, RecursionError):
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
    ``pk`` ordering is imposed so the seek is well-defined. A ``pk`` tiebreak is
    appended (see :func:`_ordering_of`) and the ordering re-applied to the queryset so
    the SQL ``ORDER BY`` and the seek predicate stay in lockstep. Deep pages are O(1):
    the seek predicate uses indexed comparisons instead of a growing ``OFFSET``.
    """
    size = clamp_limit(limit)
    ordering = _ordering_of(queryset)
    if not ordering:
        pk = queryset.model._meta.pk
        pk_name = pk.name if pk is not None else "id"
        ordering = [(pk_name, False)]
    # Re-apply the (pk-tie-broken) ordering so the SQL ``ORDER BY`` matches the seek
    # predicate exactly: an appended pk tiebreak the database did not actually order
    # by would let a tied row duplicate or skip at a page boundary.
    queryset = queryset.order_by(
        *(f"-{name}" if descending else name for name, descending in ordering)
    )
    values = _decode(cursor, queryset.model, ordering)
    if values is not None:
        queryset = queryset.filter(_seek_predicate(ordering, values))
    window = list(queryset[: size + 1])
    has_more = len(window) > size
    items = window[:size]
    next_cursor = _encode(items[-1], ordering) if has_more and items else None
    return items, next_cursor
