"""Public read API for creators + search (SDLC 09 §4, E11/B2).

All endpoints are anonymous reads (discovery/profile are public; 19+ gating is
B3). Follower/post counts are annotated so the list stays a single query. The
``following`` flag is always ``False`` here — it becomes per-user once auth
lands (B3), read from the social graph.
"""

from __future__ import annotations

import uuid

from django.db.models import Count, QuerySet
from django.http import HttpRequest
from ninja import Router, Schema

from apps.commerce.models import Product
from apps.creator.models import Creator
from config.api import api
from config.pagination import paginate

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


def _annotated() -> QuerySet[Creator]:
    """Creators with derived follower/post counts (distinct to avoid join fan-out).

    ``distinct=True`` keeps both counts correct despite the two-relation join
    fan-out. At scale the intermediate row explosion is a perf cost — move to
    subquery counts or denormalised counters then (tracked, non-blocking for B2).
    """
    return Creator.objects.annotate(
        followers_count=Count("followers", distinct=True),
        posts_count=Count("posts", distinct=True),
    )


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
        following=False,
    )


@creators_router.get("", response=CreatorPage)
def list_creators(
    request: HttpRequest,
    cursor: str | None = None,
    limit: int | None = None,
    category: str | None = None,
) -> CreatorPage:
    """List creators (optionally filtered by category), cursor-paginated."""
    del request
    queryset = _annotated().order_by("handle")
    if category:
        queryset = queryset.filter(category=category)
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return CreatorPage(items=[_creator_out(c) for c in items], next_cursor=next_cursor)


@creators_router.get("/{handle}", response={200: CreatorOut, 404: ErrorOut})
def get_creator(
    request: HttpRequest, handle: str
) -> tuple[int, CreatorOut | ErrorOut]:
    """Fetch a single creator by handle; 404 if unknown (no existence leak)."""
    del request
    creator = _annotated().filter(handle=handle).first()
    if creator is None:
        return 404, ErrorOut(detail="creator not found")
    return 200, _creator_out(creator)


@search_router.get("", response=SearchOut)
def search(request: HttpRequest, q: str = "") -> SearchOut:
    """Search creators (name/handle) and products (title) by a query string."""
    del request
    # Bound the term so an oversized query can't drive an unbounded LIKE scan.
    term = q.strip()[:_SEARCH_TERM_MAX]
    if not term:
        return SearchOut(creators=[], products=[])
    creators = list(
        _annotated()
        .filter(name__icontains=term)
        .order_by("handle")[:_SEARCH_LIMIT]
    ) + list(
        _annotated()
        .filter(handle__icontains=term)
        .exclude(name__icontains=term)
        .order_by("handle")[:_SEARCH_LIMIT]
    )
    products = Product.objects.filter(title__icontains=term).order_by("-created_at")[:_SEARCH_LIMIT]
    return SearchOut(
        creators=[_creator_out(c) for c in creators[:_SEARCH_LIMIT]],
        products=[
            ProductBrief(id=p.id, type=p.type, title=p.title, price=p.price, meta=p.meta)
            for p in products
        ],
    )


api.add_router("/creators", creators_router)
api.add_router("/search", search_router)
