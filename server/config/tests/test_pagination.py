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
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.identity.models import Account, AnonymousSession
from config.pagination import (
    DEFAULT_LIMIT,
    MAX_CURSOR_LEN,
    MAX_LIMIT,
    clamp_limit,
    paginate,
)

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


def test_oversized_nested_json_bomb_cursor_falls_back_to_start() -> None:
    """The demonstrated exploit — a huge nested-JSON bomb — degrades to the first page.

    base64 of a deeply nested ``[[[…]]]`` array is the reported crash vector: the
    length guard rejects it *before* any base64 decode or JSON parse, so a hostile
    caller can't force an expensive expand/parse. Over-length ⇒ treated as "start"
    like any other malformed cursor, never an unhandled 500.
    """
    _seed(2)
    queryset = AnonymousSession.objects.order_by("id")
    depth = 60_000
    bomb = base64.urlsafe_b64encode(b"[" * depth + b"]" * depth).decode()
    assert len(bomb) > MAX_CURSOR_LEN  # rejected by the length guard, never decoded
    items, _ = paginate(queryset, cursor=bomb, limit=10)
    assert len(items) == 2  # tolerated → treated as "start", no 500


def test_recursion_error_during_decode_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A nested-JSON bomb reaching ``json.loads`` is caught (RecursionError), not a 500.

    ``json.loads`` raises ``RecursionError`` (not ``ValueError``) on a deeply nested
    array, so that type must be in the decode ``except`` clause. The length guard
    normally stops such a token first; here the bound is lifted so the bomb reaches
    ``json.loads`` and exercises the ``except`` clause directly — defence in depth
    behind the length guard.
    """
    _seed(2)
    monkeypatch.setattr("config.pagination.MAX_CURSOR_LEN", 10_000_000)
    queryset = AnonymousSession.objects.order_by("id")
    depth = 60_000
    bomb = base64.urlsafe_b64encode(b"[" * depth + b"]" * depth).decode()
    items, _ = paginate(queryset, cursor=bomb, limit=10)
    assert len(items) == 2  # RecursionError caught → treated as "start", no 500


def test_keyset_is_stable_when_rows_are_inserted_between_pages() -> None:
    """Keyset walk never duplicates or skips a row when the list moves mid-walk.

    Ordered newest-first (``-id`` simulates top insertion), two new rows arriving at
    the head after page 1 must not shift the page-2 window: an offset cursor would
    have re-shown the two head rows (a duplicate + a skip), the keyset seek anchors
    on the last row seen and continues cleanly below it.
    """
    # Capture the ACTUAL pks — the id sequence need not start at 1. Postgres
    # sequences are not rolled back with the test transaction, so a prior test in
    # the same DB may have advanced it; the stability guarantee is about relative
    # order, not absolute id values (this test previously hard-coded 1..4 and so
    # only held on a fresh sqlite in-memory DB — a Postgres-parity fix).
    first = [AnonymousSession.objects.create() for _ in range(4)]
    ids_desc = sorted((s.pk for s in first), reverse=True)  # newest(highest)-first
    queryset = AnonymousSession.objects.order_by("-id")
    page1, cursor1 = paginate(queryset, cursor=None, limit=2)
    assert [s.pk for s in page1] == ids_desc[:2]  # top two
    assert cursor1 is not None

    for _ in range(2):  # two new rows arrive at the "top" (higher ids) mid-walk
        AnonymousSession.objects.create()

    page2, cursor2 = paginate(queryset, cursor=cursor1, limit=2)
    assert [s.pk for s in page2] == ids_desc[2:]  # continues strictly below page1's last
    assert cursor2 is None  # walk terminates; the head inserts are simply not in this walk
    walked = [s.pk for s in (*page1, *page2)]
    assert walked == ids_desc  # no duplicate, no skip across the boundary
    assert len(set(walked)) == 4


def test_pk_tiebreak_prevents_skip_on_a_non_unique_key() -> None:
    """A non-unique single sort key never skips a tied row: pk is appended as tiebreak.

    Five rows share one ``nickname``; ordered by that single non-unique key alone, a
    seek on ``nickname`` would (after page 1) find no ``nickname > v`` row and stop,
    silently dropping rows 3–5. The auto-appended ``pk`` tiebreak makes the seek a
    total order, so the walk covers every row exactly once, no skip and no duplicate.
    """
    accounts = [Account.objects.create(nickname="dup") for _ in range(5)]
    queryset = Account.objects.filter(nickname="dup").order_by("nickname")
    walked: list[int] = []
    cursor: str | None = None
    for _ in range(10):  # generous bound; the walk terminates well before this
        page, cursor = paginate(queryset, cursor=cursor, limit=2)
        walked.extend(a.pk for a in page)
        if cursor is None:
            break
    assert sorted(walked) == sorted(a.pk for a in accounts)  # all 5, none skipped
    assert len(walked) == len(set(walked))  # none duplicated


def test_datetime_tie_across_a_page_boundary_is_not_skipped() -> None:
    """A datetime tie straddling a page boundary keeps both rows (pk tiebreak).

    Rows carry ``created_at`` ``[t0, t1, t1, t2]``; paged ascending by ``created_at``
    at size 2 the boundary lands *inside* the ``t1`` tie. A seek on ``created_at``
    alone resumes at ``created_at > t1`` and skips the second ``t1`` row; the appended
    ``pk`` tiebreak resumes at ``(created_at = t1 AND pk > last)`` and keeps it.
    """
    sessions = [AnonymousSession.objects.create() for _ in range(4)]
    base = timezone.now()
    one, two = base + timedelta(seconds=1), base + timedelta(seconds=2)
    stamps = [base, one, one, two]  # rows 2 and 3 tie at ``one``
    for session, stamp in zip(sessions, stamps, strict=True):
        # ``created_at`` is auto_now_add; a bare UPDATE bypasses it to seat the tie.
        AnonymousSession.objects.filter(pk=session.pk).update(created_at=stamp)
    queryset = AnonymousSession.objects.order_by("created_at")
    page1, cursor1 = paginate(queryset, cursor=None, limit=2)
    assert cursor1 is not None  # more remains after the tie boundary
    page2, _ = paginate(queryset, cursor=cursor1, limit=2)
    walked = [s.pk for s in (*page1, *page2)]
    assert sorted(walked) == sorted(s.pk for s in sessions)  # the t1 tie stays intact
    assert len(walked) == 4 and len(set(walked)) == 4  # no skip, no duplicate


def test_uuid_sort_key_round_trips_through_the_cursor() -> None:
    """A ``UUID`` ordering value survives the encode→decode round trip (no dup/skip).

    ``anonymous_id`` is a ``UUIDField``; the cursor encodes it as its canonical string
    and ``Field.to_python`` rebuilds the ``UUID`` on decode, so the seek compares real
    UUIDs. Walking the whole list in unit pages visits every row exactly once.
    """
    sessions = [AnonymousSession.objects.create() for _ in range(5)]
    queryset = AnonymousSession.objects.order_by("anonymous_id")
    walked: list[int] = []
    cursor: str | None = None
    for _ in range(10):
        page, cursor = paginate(queryset, cursor=cursor, limit=1)
        walked.extend(s.pk for s in page)
        if cursor is None:
            break
    assert sorted(walked) == sorted(s.pk for s in sessions)
    assert len(walked) == len(set(walked)) == 5


def test_nullable_sort_key_drops_cursor_instead_of_500() -> None:
    """A nullable leading sort key that is ``None`` drops the cursor, never 500s.

    ``_encode`` cannot seat a ``> value`` seek on a ``None`` value, so it returns no
    cursor: the page degrades to "last page" (the safe fallback for an ordering a seek
    cannot drive) rather than emitting a ``"None"`` token or raising. ``kyc_verified_at``
    defaults to ``None`` on a fresh account.
    """
    for _ in range(5):
        Account.objects.create()  # kyc_verified_at defaults to None
    queryset = Account.objects.order_by("kyc_verified_at")
    items, next_cursor = paginate(queryset, cursor=None, limit=2)
    assert len(items) == 2  # a page still returns — no crash
    assert next_cursor is None  # None sort value → cursor dropped (no 500, no "None" token)


def test_annotated_sort_key_falls_back_to_pk_and_does_not_loop() -> None:
    """An annotation-alias ordering degrades to a stable pk seek — no first-page loop.

    An annotated alias is a string (passes ``_ordering_of``'s string check) and lives as
    an instance attr (so ``_encode`` could emit a cursor), but ``get_field(alias)`` fails
    on decode: a cursor that never seeks would refetch page 1 forever. ``_ordering_of``
    rejects any non-concrete key up front → pk-only fallback, so the walk advances past
    every row exactly once and terminates.
    """
    from django.db.models import IntegerField, Value

    for _ in range(5):
        Account.objects.create()
    queryset = Account.objects.annotate(
        rank=Value(1, output_field=IntegerField())
    ).order_by("-rank")
    seen: set[object] = set()
    cursor: str | None = None
    for _ in range(10):  # bounded: a page-1 loop would never terminate / would dup rows
        items, cursor = paginate(queryset, cursor=cursor, limit=2)
        for item in items:
            assert item.pk not in seen  # no duplicate → not stuck on page 1
            seen.add(item.pk)
        if cursor is None:
            break
    assert len(seen) == 5  # every row walked exactly once
