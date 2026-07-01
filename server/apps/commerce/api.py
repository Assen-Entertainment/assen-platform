"""Public read API for the product catalog (SDLC 09 §4, E11/B2).

Read-only listing. Ordering / checkout / payment are **gated** (B7) and absent.
Filter to a creator via ``?creator_id=`` and to a kind via ``?product_type=``.
"""

from __future__ import annotations

import uuid

from django.http import HttpRequest
from ninja import Router, Schema

from apps.commerce.models import Product
from config.api import api
from config.pagination import paginate

products_router = Router(tags=["commerce"])


class ProductOut(Schema):
    """Catalog listing (maps to the frontend ``Product`` type)."""

    id: uuid.UUID
    creator_id: uuid.UUID | None = None
    type: str
    title: str
    price: int
    meta: str
    media_url: str


class ProductPage(Schema):
    """One page of products plus the next cursor."""

    items: list[ProductOut]
    next_cursor: str | None = None


def _product_out(product: Product) -> ProductOut:
    """Build the product response."""
    return ProductOut(
        id=product.id,
        creator_id=product.creator_id,
        type=product.type,
        title=product.title,
        price=product.price,
        meta=product.meta,
        media_url=product.media_url,
    )


@products_router.get("", response=ProductPage)
def list_products(
    request: HttpRequest,
    creator_id: uuid.UUID | None = None,
    product_type: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> ProductPage:
    """List catalog products; filter by creator and/or type, cursor-paginated."""
    del request
    queryset = Product.objects.order_by("-created_at", "id")
    if creator_id is not None:
        queryset = queryset.filter(creator_id=creator_id)
    if product_type:
        queryset = queryset.filter(type=product_type)
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return ProductPage(items=[_product_out(p) for p in items], next_cursor=next_cursor)


api.add_router("/products", products_router)
