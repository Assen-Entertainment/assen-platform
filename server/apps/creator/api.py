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

import uuid
from typing import cast

from django.conf import settings
from django.db.models import Count, Exists, OuterRef, QuerySet
from django.http import HttpRequest
from ninja import Router, Schema
from pydantic import Field

from apps.commerce.models import Product, ProductStatus
from apps.creator.models import Creator
from apps.identity.auth import fan_auth, resolve_optional_account
from apps.identity.models import Account
from apps.social.models import Follow
from config.api import api
from config.pagination import paginate
from config.throttle import user_write_throttle

creators_router = Router(tags=["creator"])
search_router = Router(tags=["search"])

_SEARCH_LIMIT = 10
_SEARCH_TERM_MAX = 100


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
    """Search results across creators and products."""

    creators: list[CreatorOut]
    products: list[ProductBrief]


def _annotated(account: Account | None = None) -> QuerySet[Creator]:
    """Creators with derived follower/post counts (distinct to avoid join fan-out).

    ``distinct=True`` keeps both counts correct despite the two-relation join
    fan-out. At scale the intermediate row explosion is a perf cost — move to
    subquery counts or denormalised counters then (tracked, non-blocking for B2).

    When ``account`` is given, a per-user ``is_following`` flag is annotated via a
    single ``Exists`` subquery — no extra per-row query. Anonymous callers pass
    ``None`` and get no annotation (``following`` False).
    """
    queryset = Creator.objects.annotate(
        followers_count=Count("followers", distinct=True),
        posts_count=Count("posts", distinct=True),
    )
    if account is not None:
        queryset = queryset.annotate(
            is_following=Exists(
                Follow.objects.filter(creator=OuterRef("pk"), follower=account)
            )
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
    )


@creators_router.get("", response=CreatorPage)
def list_creators(
    request: HttpRequest,
    cursor: str | None = None,
    limit: int | None = None,
    category: str | None = None,
) -> CreatorPage:
    """List creators (optionally filtered by category), cursor-paginated."""
    account = resolve_optional_account(request)
    queryset = _annotated(account).order_by("handle")
    if category:
        queryset = queryset.filter(category=category)
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return CreatorPage(items=[_creator_out(c) for c in items], next_cursor=next_cursor)


@creators_router.get("/{handle}", response={200: CreatorOut, 404: ErrorOut})
def get_creator(
    request: HttpRequest, handle: str
) -> tuple[int, CreatorOut | ErrorOut]:
    """Fetch a single creator by handle; 404 if unknown (no existence leak)."""
    creator = _annotated(resolve_optional_account(request)).filter(handle=handle).first()
    if creator is None:
        return 404, ErrorOut(detail="creator not found")
    return 200, _creator_out(creator)


@search_router.get("", response=SearchOut)
def search(request: HttpRequest, q: str = "") -> SearchOut:
    """Search creators (name/handle) and products (title) by a query string."""
    account = resolve_optional_account(request)
    # Bound the term so an oversized query can't drive an unbounded LIKE scan.
    term = q.strip()[:_SEARCH_TERM_MAX]
    if not term:
        return SearchOut(creators=[], products=[])
    creators = list(
        _annotated(account)
        .filter(name__icontains=term)
        .order_by("handle")[:_SEARCH_LIMIT]
    ) + list(
        _annotated(account)
        .filter(handle__icontains=term)
        .exclude(name__icontains=term)
        .order_by("handle")[:_SEARCH_LIMIT]
    )
    # 19+ / visibility gate on product results (same invariant as list_products):
    # draft/hidden are owner-only, and adult_only follows the ENABLE_ADULT_CONTENT +
    # adult_verified gate (off → hidden from everyone), so search cannot leak them.
    product_qs = Product.objects.filter(title__icontains=term).exclude(
        status__in=(ProductStatus.DRAFT.value, ProductStatus.HIDDEN.value)
    )
    if not (
        settings.ENABLE_ADULT_CONTENT and account is not None and account.adult_verified
    ):
        product_qs = product_qs.exclude(adult_only=True)
    products = product_qs.order_by("-created_at")[:_SEARCH_LIMIT]
    return SearchOut(
        creators=[_creator_out(c) for c in creators[:_SEARCH_LIMIT]],
        products=[
            ProductBrief(id=p.id, type=p.type, title=p.title, price=p.price, meta=p.meta)
            for p in products
        ],
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
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    creator = Creator.objects.filter(owner=account).first()
    if creator is None:
        return 403, ErrorOut(detail="크리에이터만 프로필을 수정할 수 있어요.")
    if payload.name is not None:
        creator.name = payload.name
    if payload.bio is not None:
        creator.bio = payload.bio
    if payload.avatar_url is not None:
        creator.avatar_url = payload.avatar_url
    if payload.cover_url is not None:
        creator.cover_url = payload.cover_url
    if payload.accent_color is not None:
        creator.accent_color = payload.accent_color
    if payload.category is not None:
        creator.category = payload.category
    creator.save()
    # Re-fetch through the annotated queryset so the response carries the derived
    # follower/post counts and the caller's own following flag, like every read.
    annotated = _annotated(account).get(pk=creator.pk)
    return 200, _creator_out(annotated)


api.add_router("/studio/profile", studio_profile_router)
