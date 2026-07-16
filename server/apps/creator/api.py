"""Public read API for creators + search (SDLC 09 §4, E11/B2).

All endpoints are anonymous reads (discovery/profile are public; 19+ gating is
B3). Follower/post counts are annotated so the list stays a single query. The
``following`` flag is per-user (E11/B4): anonymous callers always see ``False``,
while an authenticated one gets their real follow state derived from the social
graph via a single ``Exists`` subquery (no N+1, and the anonymous read is never
broken). Auth is resolved silently with
:func:`~apps.identity.auth.resolve_optional_account`.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import (
    Case,
    Count,
    Exists,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from ninja import Router, Schema
from pydantic import Field

from apps.commerce.models import OrderItem, OrderStatus, Product, ProductStatus
from apps.content.models import Post
from apps.creator.models import Creator
from apps.identity.auth import (
    authed,
    fan_auth,
    require_kyc_verified,
    resolve_optional_account,
)
from apps.identity.models import Account
from apps.membership.models import Subscription, SubscriptionStatus
from apps.social.models import CreatorBlock, Follow, blocked_creator_ids
from config.api import api
from config.errors import ErrorCode
from config.pagination import clamp_limit, paginate
from config.patch import apply_optional
from config.throttle import user_write_throttle

creators_router = Router(tags=["creator"])
search_router = Router(tags=["search"])

_SEARCH_LIMIT = 10  # default search page size
_SEARCH_LIMIT_MAX = 50  # hard ceiling per search page
_SEARCH_TERM_MAX = 100

# Server-ranked discovery surfaces (E11) — the web sections wire to these instead
# of client-side sort/reverse of a single list. Each maps to a stable ORDER BY over
# the annotated creator queryset (followers_count is derived in `_annotated`).
_RECOMMENDATION_SORTS: dict[str, tuple[str, ...]] = {
    "popular": ("-followers_count", "handle"),
    "new": ("-created_at", "handle"),
    "recommended": ("-followers_count", "-created_at", "handle"),
}


class ErrorOut(Schema):
    """Stable error shape for creator endpoints."""

    detail: str


class CreatorOut(Schema):
    """Creator profile (maps to the frontend ``Creator`` type)."""

    id: uuid.UUID
    handle: str
    name: str
    bio: str
    accent_color: str
    avatar_url: str
    cover_url: str
    category: str
    verified: bool
    followers: int
    posts: int
    following: bool = False
    # True only when the authenticated caller has *personally* blocked this creator
    # (apps.social.CreatorBlock). Discovery/search already exclude blocked creators,
    # so this is meaningful on explicit single navigation (get_creator) where the
    # creator is returned and the web renders a "blocked" state. Anonymous → False.
    blocked: bool = False


class CreatorPage(Schema):
    """One page of creators plus the cursor for the next page."""

    items: list[CreatorOut]
    next_cursor: str | None = None


class ProductBrief(Schema):
    """Minimal product shape for search results."""

    id: uuid.UUID
    type: str
    title: str
    price: int
    meta: str


class SearchOut(Schema):
    """Search results across creators and products (ranked, paginated)."""

    creators: list[CreatorOut]
    products: list[ProductBrief]
    # Offset to request the next page, or None when neither result set is full.
    next_offset: int | None = None


def _adult_allowed(account: Account | None) -> bool:
    """Whether 19+ (``adult_only``) items may be counted/shown for ``account``.

    Mirrors ``apps.content.api._adult_allowed`` (the single funnel every public post
    read uses): fail-closed — ``ENABLE_ADULT_CONTENT`` off hides adult items from
    EVERYONE; on, only an ``adult_verified`` viewer counts them.
    """
    return bool(
        settings.ENABLE_ADULT_CONTENT and account is not None and account.adult_verified
    )


def _visible_posts(account: Account | None) -> QuerySet[Post]:
    """Posts a given viewer may see, gated by the 19+ rule (:func:`_adult_allowed`).

    Used as the relation for the creator ``posts`` count so the count applies the SAME
    adult gate as the post *list* (``apps.content.api._post_qs``). Without this the
    count leaked the existence of hidden adult posts (list 0 / count 1, ASS-296 #12).
    """
    posts = Post.objects.all()
    if not _adult_allowed(account):
        posts = posts.exclude(adult_only=True)
    return posts


def _creator_relation_count(relation: QuerySet[Any]) -> Coalesce:
    """A correlated ``COUNT(*)`` of ``relation`` rows for the outer creator, 0 when none.

    ``relation`` is a queryset over a model with a ``creator`` FK (``Follow`` /
    ``Post``). Grouping by that FK under a ``creator=OuterRef("pk")`` filter yields one
    aggregate row per creator, so the subquery returns a single scalar; ``Coalesce(…,
    0)`` maps the "no related rows" NULL to 0.
    """
    per_creator = (
        relation.filter(creator=OuterRef("pk"))
        .order_by()
        .values("creator")
        .annotate(count=Count("*"))
        .values("count")
    )
    return Coalesce(Subquery(per_creator, output_field=IntegerField()), 0)


def _annotated(account: Account | None = None) -> QuerySet[Creator]:
    """Creators with derived follower/post counts via per-relation subqueries.

    Each count is a correlated scalar subquery (:func:`_creator_relation_count`), so
    the follower and post counts stay independent instead of multiplying into one
    another. The previous ``Count(..., distinct=True)`` over a double join was correct
    but paid an O(followers × posts) intermediate row explosion per creator before the
    ``DISTINCT`` collapse; the subqueries make each an O(followers)+O(posts) indexed
    aggregate that no longer degrades as either relation grows.

    When ``account`` is given, per-user ``is_following`` / ``is_blocked`` flags are
    annotated via single ``Exists`` subqueries — no extra per-row query. Anonymous
    callers pass ``None`` and get no annotation (``following`` / ``blocked`` False).
    """
    queryset = Creator.objects.annotate(
        followers_count=_creator_relation_count(Follow.objects.all()),
        # 19+ gate: count only posts this viewer may see, so the public ``posts`` count
        # matches the gated post list and never leaks hidden adult posts (ASS-296 #12).
        posts_count=_creator_relation_count(_visible_posts(account)),
    )
    if account is not None:
        queryset = queryset.annotate(
            is_following=Exists(
                Follow.objects.filter(creator=OuterRef("pk"), follower=account)
            ),
            is_blocked=Exists(
                CreatorBlock.objects.filter(creator=OuterRef("pk"), blocker=account)
            ),
        )
    return queryset


def _creator_out(creator: Creator) -> CreatorOut:
    """Build the creator response from an annotated row."""
    return CreatorOut(
        id=creator.id,
        handle=creator.handle,
        name=creator.name,
        bio=creator.bio,
        accent_color=creator.accent_color,
        avatar_url=creator.avatar_url,
        cover_url=creator.cover_url,
        category=creator.category,
        verified=creator.verified,
        followers=getattr(creator, "followers_count", 0),
        posts=getattr(creator, "posts_count", 0),
        following=bool(getattr(creator, "is_following", False)),
        blocked=bool(getattr(creator, "is_blocked", False)),
    )


@creators_router.get("", response=CreatorPage)
def list_creators(
    request: HttpRequest,
    cursor: str | None = None,
    limit: int | None = None,
    category: str | None = None,
    sort: str | None = None,
) -> CreatorPage:
    """List creators (optionally filtered by category), cursor-paginated.

    Discovery is an aggregate surface, so creators the authenticated caller has
    personally blocked are excluded (anonymous callers block nothing).

    ``sort`` selects a server-ranked discovery surface (``popular`` / ``new`` /
    ``recommended`` — see :data:`_RECOMMENDATION_SORTS`), computed from real
    follower/recency signals rather than the client sorting a single list. A ranked
    surface returns one bounded top-N page (``next_cursor`` is None) because keyset
    cursors assume the stable handle order; the default (no ``sort``) stays
    cursor-paginated.
    """
    account = resolve_optional_account(request)
    # Only published creators are discoverable; an unpublished (e.g. withdrawn-owner)
    # profile drops out of the aggregate surface.
    queryset = (
        _annotated(account)
        .filter(published=True)
        .exclude(id__in=blocked_creator_ids(account))
    )
    if category:
        queryset = queryset.filter(category=category)
    ordering = _RECOMMENDATION_SORTS.get(sort or "")
    if ordering is not None:
        ranked = list(queryset.order_by(*ordering)[: clamp_limit(limit)])
        return CreatorPage(
            items=[_creator_out(c) for c in ranked], next_cursor=None
        )
    items, next_cursor = paginate(queryset.order_by("handle"), cursor=cursor, limit=limit)
    return CreatorPage(items=[_creator_out(c) for c in items], next_cursor=next_cursor)


@creators_router.get("/{handle}", response={200: CreatorOut, 404: ErrorOut})
def get_creator(
    request: HttpRequest, handle: str
) -> tuple[int, CreatorOut | ErrorOut]:
    """Fetch a single creator by handle; 404 if unknown (no existence leak).

    An unpublished profile (``published=False`` — e.g. the owner withdrew) 404s just
    like an unknown handle, so an offboarded creator's page is no longer viewable.
    """
    creator = (
        _annotated(resolve_optional_account(request))
        .filter(handle=handle, published=True)
        .first()
    )
    if creator is None:
        return 404, ErrorOut(detail="creator not found")
    return 200, _creator_out(creator)


class FollowerOut(Schema):
    """One follower of a creator — already-public display identity only.

    Carries only fields that are already public elsewhere: the follower's
    ``nickname`` (shown on comments and in follow notifications) and, when the
    follower themselves operates a creator, that creator's ``handle``/
    ``avatar_url`` so the row can link to their profile. No contact/identity PII
    (phone, birth date, etc.) is ever exposed here.
    """

    id: uuid.UUID
    nickname: str
    is_creator: bool
    handle: str = ""
    avatar_url: str = ""


class FollowerPage(Schema):
    """One keyset page of a creator's followers plus the next-page cursor."""

    items: list[FollowerOut]
    next_cursor: str | None = None


def _follower_out(follow: Follow) -> FollowerOut:
    """Build a public follower row from a follow edge (nickname + creator link).

    The follower's own creator profile (reverse 1:1 ``creator_profile``) is
    read to add a profile link when they are a creator; a plain fan has none.
    """
    account = follow.follower
    try:
        creator: Creator | None = account.creator_profile
    except Creator.DoesNotExist:
        creator = None
    return FollowerOut(
        id=follow.id,
        nickname=account.nickname,
        is_creator=creator is not None,
        handle=creator.handle if creator is not None else "",
        avatar_url=creator.avatar_url if creator is not None else "",
    )


@creators_router.get(
    "/{handle}/followers", response={200: FollowerPage, 404: ErrorOut}
)
def list_followers(
    request: HttpRequest,
    handle: str,
    cursor: str | None = None,
    limit: int | None = None,
) -> tuple[int, FollowerPage | ErrorOut]:
    """List a creator's followers, newest first (public, keyset-paginated).

    A public read: a follower's ``nickname`` is already public (comments, follow
    notifications), so listing followers introduces no new PII exposure. Withdrawn
    (deactivated) accounts are excluded so an anonymised fan is not surfaced. A
    404 for an unknown handle keeps parity with the profile read (no existence
    leak). ``select_related`` folds the follower + their optional creator profile
    into the page query so the row build stays O(page), not O(followers).
    """
    creator = Creator.objects.filter(handle=handle).first()
    if creator is None:
        return 404, ErrorOut(detail="creator not found")
    followers = (
        Follow.objects.filter(creator=creator, follower__is_active=True)
        .select_related("follower__creator_profile")
        .order_by("-created_at", "id")
    )
    items, next_cursor = paginate(followers, cursor=cursor, limit=limit)
    return 200, FollowerPage(
        items=[_follower_out(f) for f in items], next_cursor=next_cursor
    )


@search_router.get("", response=SearchOut)
def search(
    request: HttpRequest, q: str = "", limit: int | None = None, offset: int = 0
) -> SearchOut:
    """Ranked, paginated search over creators and products.

    Creators match on name/handle/bio/category and products on title/meta/
    description — multi-field substring (``icontains``). Substring (not a
    whitespace ``tsvector``) is deliberate: Korean has no inter-morpheme spaces, so
    a ``simple``-config full-text index would miss most intra-word matches. A
    pg_trgm GIN index (indexed substring + typo tolerance) is the documented
    scale/fuzzy follow-up (ASS-273). Results are ranked so the best hits lead — an
    exact name, then a prefix, then any-field contains — and ``limit``/``offset``
    page them; ``next_offset`` is set when a further page may exist.
    """
    account = resolve_optional_account(request)
    # Bound the term so an oversized query can't drive an unbounded LIKE scan.
    term = q.strip()[:_SEARCH_TERM_MAX]
    if not term:
        return SearchOut(creators=[], products=[])
    size = max(1, min(limit or _SEARCH_LIMIT, _SEARCH_LIMIT_MAX))
    offset = max(0, offset)
    # Search is an aggregate surface: personally blocked creators AND their products
    # are excluded for the authenticated caller (anonymous blocks nothing).
    blocked = blocked_creator_ids(account)
    creator_qs = (
        _annotated(account)
        .filter(published=True)
        .filter(
            Q(name__icontains=term)
            | Q(handle__icontains=term)
            | Q(bio__icontains=term)
            | Q(category__icontains=term)
        )
        .exclude(id__in=blocked)
        .annotate(
            match_rank=Case(
                When(name__iexact=term, then=Value(0)),
                When(name__istartswith=term, then=Value(1)),
                When(name__icontains=term, then=Value(2)),
                When(handle__icontains=term, then=Value(3)),
                default=Value(4),
                output_field=IntegerField(),
            )
        )
        # ``match_rank``/``followers_count`` are annotations added above and in
        # ``_annotated``; django-stubs 6 can't resolve annotated fields inside
        # order_by (a known plugin limitation — valid at runtime, covered by tests).
        .order_by("match_rank", "-followers_count", "handle")  # type: ignore[misc]
    )
    # Fetch one past the page to detect whether a further page exists.
    creators = list(creator_qs[offset : offset + size + 1])
    # 19+ / visibility gate on product results (same invariant as list_products):
    # draft/hidden are owner-only, and adult_only follows the ENABLE_ADULT_CONTENT +
    # adult_verified gate (off → hidden from everyone), so search cannot leak them.
    product_qs = (
        Product.objects.filter(
            Q(title__icontains=term)
            | Q(meta__icontains=term)
            | Q(description__icontains=term)
        )
        .exclude(status__in=(ProductStatus.DRAFT.value, ProductStatus.HIDDEN.value))
        .exclude(creator_id__in=blocked)
    )
    if not (
        settings.ENABLE_ADULT_CONTENT and account is not None and account.adult_verified
    ):
        product_qs = product_qs.exclude(adult_only=True)
    product_qs = product_qs.annotate(
        match_rank=Case(
            When(title__istartswith=term, then=Value(0)),
            When(title__icontains=term, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    ).order_by("match_rank", "-created_at")
    products = list(product_qs[offset : offset + size + 1])
    more = len(creators) > size or len(products) > size
    return SearchOut(
        creators=[_creator_out(c) for c in creators[:size]],
        products=[
            ProductBrief(id=p.id, type=p.type, title=p.title, price=p.price, meta=p.meta)
            for p in products[:size]
        ],
        next_offset=(offset + size) if more else None,
    )


api.add_router("/creators", creators_router)
api.add_router("/search", search_router)


# --------------------------------------------------------------------------- #
# Studio (owner profile edit; R3 — pure engineering, 법무 무관).
# The scope is always the caller's OWN creator profile (``owner=account``), never
# taken from the body, so a fan can only edit the creator they operate.
# --------------------------------------------------------------------------- #
studio_profile_router = Router(auth=fan_auth, tags=["studio-creator"])


class StudioProfilePatch(Schema):
    """Owner payload to update the caller's own creator profile (provided fields only)."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    bio: str | None = Field(default=None, max_length=2000)
    avatar_url: str | None = Field(default=None, max_length=500)
    cover_url: str | None = Field(default=None, max_length=500)
    accent_color: str | None = Field(default=None, max_length=9)
    category: str | None = Field(default=None, max_length=40)


@studio_profile_router.patch(
    "",
    response={200: CreatorOut, 403: ErrorOut},
    throttle=user_write_throttle("30/min"),
)
def studio_update_profile(
    request: HttpRequest, payload: StudioProfilePatch
) -> tuple[int, CreatorOut | ErrorOut]:
    """Update the caller's own creator profile; 403 if they operate no creator."""
    account = authed(request)
    creator = Creator.objects.filter(owner=account).first()
    if creator is None:
        return 403, ErrorOut(detail="크리에이터만 프로필을 수정할 수 있어요.")
    apply_optional(
        creator,
        payload,
        ["name", "bio", "avatar_url", "cover_url", "accent_color", "category"],
    )
    creator.save()
    # Re-fetch through the annotated queryset so the response carries the derived
    # follower/post counts and the caller's own following flag, like every read.
    annotated = _annotated(account).get(pk=creator.pk)
    return 200, _creator_out(annotated)


# Handles that could impersonate the platform or collide with reserved surfaces.
_RESERVED_HANDLES = frozenset(
    {"admin", "api", "studio", "me", "support", "official", "assen", "help", "settings"}
)


class StudioProfileCreateIn(Schema):
    """Payload for a fan to open (self-serve) their own creator page."""

    handle: str
    name: str


@studio_profile_router.post(
    "",
    response={201: CreatorOut, 409: ErrorOut, 422: ErrorOut},
    throttle=user_write_throttle("6/min"),
)
def studio_create_profile(
    request: HttpRequest, payload: StudioProfileCreateIn
) -> tuple[int, CreatorOut | ErrorOut]:
    """Open the caller's own creator page — the self-serve "크리에이터 되기" flow (D4).

    A signed-in fan becomes a creator by claiming a unique ``handle`` + display
    ``name``; this creates their :class:`~apps.creator.models.Creator`
    (``owner`` = the caller). "Creator" is derived from operating a creator
    profile (``handle`` present on ``/fan/me``), not a separate role — so no
    privilege change is made here. Idempotency is NOT wanted: a second call
    (already a creator, or a taken handle) is a 409, and the unique(handle) /
    one-to-one(owner) constraints close the concurrent-claim race even if two
    requests both pass the pre-checks.
    """
    account = authed(request)
    # 본인인증 gate before any side effect: becoming a creator is an interaction that
    # requires a verified fan (대표 07-16). Because this is the only fan-facing path to
    # a Creator, an existing creator is already verified — so the fan-authoring/studio
    # writes downstream inherit that guarantee without needing their own gate.
    require_kyc_verified(account)
    handle = payload.handle.strip().lower()
    name = payload.name.strip()
    if not 2 <= len(handle) <= 32 or re.fullmatch(r"[a-z0-9_]+", handle) is None:
        return 422, ErrorOut(
            detail="핸들은 소문자·숫자·밑줄(_) 2~32자로 입력해 주세요."
        )
    if not 1 <= len(name) <= 80:
        return 422, ErrorOut(detail="이름은 1~80자로 입력해 주세요.")
    if handle in _RESERVED_HANDLES:
        return 409, ErrorOut(detail="사용할 수 없는 핸들이에요.")
    if Creator.objects.filter(owner=account).exists():
        return 409, ErrorOut(detail="이미 크리에이터 페이지를 운영 중이에요.")
    if Creator.objects.filter(handle=handle).exists():
        return 409, ErrorOut(detail="이미 사용 중인 핸들이에요.")
    try:
        with transaction.atomic():
            creator = Creator.objects.create(
                owner=account, handle=handle, name=name
            )
    except IntegrityError:
        # A concurrent claim won the unique(handle) / one-to-one(owner) race.
        return 409, ErrorOut(detail="이미 사용 중인 핸들이에요.")
    annotated = _annotated(account).get(pk=creator.pk)
    return 201, _creator_out(annotated)


api.add_router("/studio/profile", studio_profile_router)


# --------------------------------------------------------------------------- #
# Studio dashboard stats (owner real counts; R4-W5 — pure engineering).
# COUNTS ONLY. No revenue/settlement/amount ever appears here — 수익·매출·정산 금액은
# 재무·법무 게이트(ASS-229) 소관이라 이 집계에서 전면 배제한다. Every figure is scoped to
# the caller's OWN creator (``owner=account``), so another creator's stats cannot
# leak. The web dashboard replaces its placeholder STATS with these.
# --------------------------------------------------------------------------- #
studio_stats_router = Router(auth=fan_auth, tags=["studio-creator"])


class StudioError(Schema):
    """Coded error for studio-owner endpoints (``detail`` + machine ``code``).

    Mirrors the commerce/membership coded-error shape so the web branches on the
    stable ``code`` (e.g. :attr:`~config.errors.ErrorCode.OWNER_REQUIRED`) rather
    than the localized ``detail`` copy.
    """

    detail: str
    code: str


class StudioStatsOut(Schema):
    """Owner dashboard real counts (maps to the studio dashboard summary).

    Every field is a pure count scoped to the caller's own creator. There is NO
    revenue/settlement/amount field by design — money figures are gated (ASS-229),
    so this endpoint carries counts only.

    - ``followers``: fans following the creator (:class:`~apps.social.models.Follow`).
    - ``posts``: the creator's feed posts.
    - ``products``: catalog products the creator owns (all statuses).
    - ``products_selling``: the subset currently ``selling`` (public on-sale).
    - ``orders``: distinct **non-cancelled** orders that contain at least one of
      the creator's products (order **count**, never an amount). A cancelled
      order never happened commercially, so it is excluded from the dashboard
      "order count" the same way a cancelled order is excluded everywhere else.
    - ``subscribers``: the creator's active subscribers (``status = active``).
    """

    followers: int
    posts: int
    products: int
    products_selling: int
    orders: int
    subscribers: int


@studio_stats_router.get("", response={200: StudioStatsOut, 403: StudioError})
def studio_stats(request: HttpRequest) -> tuple[int, StudioStatsOut | StudioError]:
    """Real per-creator dashboard counts for the caller's own creator.

    Owner-scoped: every figure is filtered to the creator this account operates, so
    another creator's stats never leak. 403 (OwnerRequired) if the caller operates
    no creator. Counts only — no revenue/settlement (ASS-229 gated).

    A handful of owner-scoped scalar aggregates (no per-row query → no N+1): the
    product total + selling counts collapse into one conditional aggregate, the
    rest are single indexed ``COUNT``s.
    """
    account = authed(request)
    creator = Creator.objects.filter(owner=account).first()
    if creator is None:
        return 403, StudioError(
            detail="크리에이터만 스튜디오 통계를 볼 수 있어요.",
            code=ErrorCode.OWNER_REQUIRED.value,
        )
    product_counts = Product.objects.filter(creator=creator).aggregate(
        total=Count("id"),
        selling=Count("id", filter=Q(status=ProductStatus.SELLING.value)),
    )
    return 200, StudioStatsOut(
        followers=Follow.objects.filter(creator=creator).count(),
        posts=Post.objects.filter(creator=creator).count(),
        products=product_counts["total"],
        products_selling=product_counts["selling"],
        # OrderItem → distinct Order: how many non-cancelled orders include this
        # creator's products (a count, never a sum of amounts). Cancelled orders
        # are excluded — they never happened commercially.
        orders=(
            OrderItem.objects.filter(product__creator=creator)
            .exclude(order__status=OrderStatus.CANCELLED.value)
            .values("order_id")
            .distinct()
            .count()
        ),
        subscribers=Subscription.objects.filter(
            creator=creator, status=SubscriptionStatus.ACTIVE.value
        ).count(),
    )


api.add_router("/studio/stats", studio_stats_router)
