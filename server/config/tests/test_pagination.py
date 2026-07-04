"""Tests locking the opaque-cursor pagination contract (ASS-257 item 4).

The web "더보기" (load-more) consumes ``{items, next_cursor}``: the cursor is an
opaque token, ``limit`` is clamped to an upper bound, and ``next_cursor`` is
``None`` exactly on the final page. These tests pin that wire contract so a later
change to the pagination internals cannot silently break the consumer.
"""

from __future__ import annotations

import base64

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
    # Opaque token: base64-decodable, not a bare integer offset the client can reason about.
    decoded = base64.urlsafe_b64decode(next_cursor.encode()).decode()
    assert decoded.isdigit()  # internal representation, but only via decode


def test_malformed_cursor_starts_from_beginning() -> None:
    _seed(2)
    queryset = AnonymousSession.objects.order_by("id")
    items, _ = paginate(queryset, cursor="!!!not-base64!!!", limit=10)
    assert len(items) == 2  # tolerated → treated as "start"
