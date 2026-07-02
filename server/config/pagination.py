"""Opaque cursor pagination for list endpoints (SDLC 09 §4 — ``Paginated<T>``).

List endpoints return ``{items, next_cursor}``. The cursor is an opaque,
base64-encoded offset so callers treat it as a token rather than an index — that
lets the implementation move to keyset pagination later without changing the
wire contract. ``next_cursor`` is ``None`` on the final page.
"""

from __future__ import annotations

import base64
import binascii

from django.db.models import Model, QuerySet

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def clamp_limit(limit: int | None) -> int:
    """Bound a client-supplied page size to ``[1, MAX_LIMIT]`` (default when None)."""
    if limit is None:
        return DEFAULT_LIMIT
    return max(1, min(limit, MAX_LIMIT))


def _encode(offset: int) -> str:
    """Encode a non-negative offset as an opaque cursor token."""
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


def _decode(cursor: str | None) -> int:
    """Decode a cursor to an offset; malformed or empty cursors mean "start"."""
    if not cursor:
        return 0
    try:
        value = int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, binascii.Error):
        return 0
    return max(value, 0)


def paginate[M: Model](
    queryset: QuerySet[M], *, cursor: str | None, limit: int | None
) -> tuple[list[M], str | None]:
    """Return one page of ``queryset`` plus the cursor for the next page.

    Fetches ``limit + 1`` rows to detect whether more remain without a second
    count query. The queryset must carry a deterministic ``order_by`` so the
    offset window is stable across requests.
    """
    size = clamp_limit(limit)
    start = _decode(cursor)
    window = list(queryset[start : start + size + 1])
    has_more = len(window) > size
    items = window[:size]
    next_cursor = _encode(start + size) if has_more else None
    return items, next_cursor
