"""Tests locking the opaque-cursor pagination contract (ASS-257 item 4).

The web "더보기" (load-more) consumes ``{items, next_cursor}``: the cursor is an
opaque token, ``limit`` is clamped to an upper bound, and ``next_cursor`` is
``None`` exactly on the final page. These tests pin that wire contract so a later
change to the pagination internals cannot silently break the consumer. The
internals are now a keyset (seek) cursor (R6-W1A); the contract tests below hold
across the offset→keyset swap, and the keyset stability guarantee (no duplicate or
skipped row when the list moves mid-walk) is pinned by its own test at the bottom.
"""

from __future__ import annotations

import base64
import json

import pytest

from apps.identity.models import AnonymousSession
from config.pagination import DEFAULT_LIMIT, MAX_LIMIT, clamp_limit, paginate

pytestmark = pytest.mark.django_db


def test_clamp_limit_bounds() -> None:
    assert clamp_limit(None) == DEFAULT_LIMIT
    assert clamp_limit(0) == 1  # floored to 1
    assert clamp_limit(-5) == 1
    assert clamp_limit(50) == 50
    assert clamp_limit(MAX_LIMIT + 1000) == MAX_LIMIT  # capped


def _seed(n: int) -> None:
    AnonymousSession.objects.bulk_create([AnonymousSession() for _ in range(n)])


def test_next_cursor_is_none_on_last_page() -> None:
    _seed(3)
    queryset = AnonymousSession.objects.order_by("id")
    items, next_cursor = paginate(queryset, cursor=None, limit=10)
    assert len(items) == 3
    assert next_cursor is None  # everything fit → final page


def test_cursor_walks_to_exactly_one_null_terminated_end() -> None:
    _seed(5)
    queryset = AnonymousSession.objects.order_by("id")
    page1, cursor1 = paginate(queryset, cursor=None, limit=2)
    assert len(page1) == 2 and cursor1 is not None
    page2, cursor2 = paginate(queryset, cursor=cursor1, limit=2)
    assert len(page2) == 2 and cursor2 is not None
    page3, cursor3 = paginate(queryset, cursor=cursor2, limit=2)
    assert len(page3) == 1  # remainder
    assert cursor3 is None  # last page terminates the walk
    # No row is repeated or skipped across the walk.
    ids = [s.pk for s in (*page1, *page2, *page3)]
    assert len(set(ids)) == 5


def test_limit_is_capped_at_max() -> None:
    _seed(MAX_LIMIT + 5)
    queryset = AnonymousSession.objects.order_by("id")
    # Ask for far more than MAX_LIMIT; the page is clamped and more remains.
    items, next_cursor = paginate(queryset, cursor=None, limit=MAX_LIMIT + 1000)
    assert len(items) == MAX_LIMIT
    assert next_cursor is not None


def test_next_cursor_is_opaque_base64() -> None:
    _seed(3)
    queryset = AnonymousSession.objects.order_by("id")
    _, next_cursor = paginate(queryset, cursor=None, limit=2)
    assert next_cursor is not None
    # Opaque token: base64-decodable, and NOT a bare integer offset the client can
    # reason about — the keyset payload is a JSON array of the last row's sort-key
    # values, so it decodes to a structure, not a single number.
    decoded = base64.urlsafe_b64decode(next_cursor.encode()).decode()
    assert not decoded.isdigit()  # never a bare offset a caller could increment
    assert isinstance(json.loads(decoded), list)  # internal shape, reachable only via decode


def test_malformed_cursor_starts_from_beginning() -> None:
    _seed(2)
    queryset = AnonymousSession.objects.order_by("id")
    items, _ = paginate(queryset, cursor="!!!not-base64!!!", limit=10)
    assert len(items) == 2  # tolerated → treated as "start"


def test_legacy_offset_cursor_falls_back_to_start() -> None:
    """An old-format base64 offset token (pre-keyset) degrades to the first page.

    The previous implementation encoded a bare integer offset; a client that still
    holds one must not error — it is treated as "start" like any malformed cursor,
    so the swap is seamless.
    """
    _seed(3)
    queryset = AnonymousSession.objects.order_by("id")
    legacy = base64.urlsafe_b64encode(b"1").decode()  # what the offset encoder emitted
    items, _ = paginate(queryset, cursor=legacy, limit=10)
    assert len(items) == 3  # arity mismatch (bare int, not a list) → start from beginning


def test_keyset_is_stable_when_rows_are_inserted_between_pages() -> None:
    """Keyset walk never duplicates or skips a row when the list moves mid-walk.

    Ordered newest-first (``-id`` simulates top insertion), two new rows arriving at
    the head after page 1 must not shift the page-2 window: an offset cursor would
    have re-shown the two head rows (a duplicate + a skip), the keyset seek anchors
    on the last row seen and continues cleanly below it.
    """
    _seed(4)  # ids 1,2,3,4
    queryset = AnonymousSession.objects.order_by("-id")
    page1, cursor1 = paginate(queryset, cursor=None, limit=2)
    assert [s.pk for s in page1] == [4, 3]
    assert cursor1 is not None

    _seed(2)  # ids 5,6 arrive at the "top" (higher ids) mid-walk

    page2, cursor2 = paginate(queryset, cursor=cursor1, limit=2)
    assert [s.pk for s in page2] == [2, 1]  # continues strictly below id=3
    assert cursor2 is None  # walk terminates; the head inserts are simply not in this walk
    walked = [s.pk for s in (*page1, *page2)]
    assert walked == [4, 3, 2, 1]  # no duplicate, no skip across the boundary
    assert len(set(walked)) == 4
