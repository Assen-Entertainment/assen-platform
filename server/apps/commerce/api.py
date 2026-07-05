"""Commerce API — product catalog (read) + mock order flow (SDLC 09 §4, B2·B4).

The product listing is read-only. B4 adds a fan order flow (``fan_auth``): place a
**mock** order (no real payment; no money moves — B7 gated), list/read one's own
orders, cancel, and request a refund. Filter the catalog to a creator via
``?creator_id=`` and to a kind via ``?product_type=``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import cast

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router, Schema
from pydantic import Field, field_validator

from apps.commerce.models import (
    Order,
    OrderItem,
    OrderStatus,
    Product,
    ProductStatus,
    ProductType,
    RefundRequest,
    RefundStatus,
)
from apps.creator.models import Creator
from apps.identity.auth import fan_auth, resolve_optional_account
from apps.identity.models import Account
from apps.notification.models import NotificationKind
from apps.notification.services import notify
from apps.social.models import blocked_creator_ids
from config.api import api
from config.errors import ErrorCode
from config.pagination import paginate
from config.throttle import user_write_throttle


def _validated_media_url(value: str) -> str:
    """Reject non-http(s) / non-relative media URLs (mirrors content.PostIn, A5).

    A product's ``media_url`` is echoed into the catalog/detail views, so an
    attacker-supplied ``javascript:``/``data:`` scheme could drive XSS. Accept only
    an absolute http(s) URL or a site-relative path; empty stays allowed (no media).
    """
    if value == "" or value.startswith(("/", "http://", "https://")):
        return value
    raise ValueError("media_url must be an http(s) URL or a site-relative path.")


def _adult_allowed(viewer: Account | None) -> bool:
    """Whether 19+ (``adult_only``) products may be shown to ``viewer``.

    Fail-closed, identical to the content gate: ``ENABLE_ADULT_CONTENT`` is False by
    default so every adult item is hidden from EVERYONE (R3 정본 §55); when on, an
    item is shown only to an ``adult_verified`` viewer.
    """
    return bool(
        settings.ENABLE_ADULT_CONTENT and viewer is not None and viewer.adult_verified
    )

products_router = Router(tags=["commerce"])
orders_router = Router(auth=fan_auth, tags=["commerce-orders"])

# Order states that may still be cancelled / refunded by the fan.
_CANCELLABLE = {OrderStatus.PAID.value, OrderStatus.SHIPPING.value}
_REFUNDABLE = {OrderStatus.SHIPPING.value, OrderStatus.COMPLETED.value}
# Refund states that count as an open request (blocks a second one).
_OPEN_REFUND = {RefundStatus.REQUESTED.value, RefundStatus.REVIEWING.value}


class CommerceError(Schema):
    """Stable error shape for commerce endpoints.

    ``detail`` is human-facing copy (display); ``code`` is the stable machine-readable
    reason the web branches on (see :class:`~config.errors.ErrorCode`).
    """

    detail: str
    code: str


class ProductOut(Schema):
    """Catalog listing (maps to the frontend ``Product`` type)."""

    id: uuid.UUID
    creator_id: uuid.UUID | None = None
    creator_name: str = ""
    type: str
    title: str
    price: int
    meta: str
    media_url: str
    description: str
    options: list[str]
    stock: int | None = None
    sold_out: bool
    locked: bool
    is_adult: bool = False


class ProductPage(Schema):
    """One page of products plus the next cursor."""

    items: list[ProductOut]
    next_cursor: str | None = None


def _product_out(product: Product) -> ProductOut:
    """Build the product response."""
    return ProductOut(
        id=product.id,
        creator_id=product.creator_id,
        # 상세/카드 표기용 소유 크리에이터명(전역 카탈로그 상품은 빈 문자열).
        creator_name=product.creator.name if product.creator is not None else "",
        type=product.type,
        title=product.title,
        price=product.price,
        meta=product.meta,
        media_url=product.media_url,
        description=product.description,
        # JSONField can hold anything; coerce defensively to list[str].
        options=[str(o) for o in product.options] if isinstance(product.options, list) else [],
        stock=product.stock,
        sold_out=product.sold_out,
        locked=product.locked,
        is_adult=product.adult_only,
    )


def _public_product_qs(viewer: Account | None) -> QuerySet[Product]:
    """Consumer-facing catalog queryset: draft/hidden and gated 19+ excluded.

    draft/hidden are owner-only (studio); adult_only follows the 19+ gate
    (:func:`_adult_allowed`). This is the single funnel for both the public list and
    the single fetch, so a direct GET of a draft/hidden/gated-adult product 404s
    (no existence leak) instead of slipping past the list filter.
    """
    queryset = Product.objects.select_related("creator").exclude(
        status__in=(ProductStatus.DRAFT.value, ProductStatus.HIDDEN.value)
    )
    if not _adult_allowed(viewer):
        queryset = queryset.exclude(adult_only=True)
    return queryset


@products_router.get("", response=ProductPage)
def list_products(
    request: HttpRequest,
    creator_id: uuid.UUID | None = None,
    product_type: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> ProductPage:
    """List catalog products; filter by creator and/or type, cursor-paginated.

    Consumer surface: draft/hidden listings and gated 19+ items are excluded
    (:func:`_public_product_qs`) — the owner manages those via ``/studio/products``.

    Personal-block gating (mirrors ``content.list_posts``): the global (unfiltered)
    browse is an aggregate surface, so products from creators the authenticated
    caller has personally blocked are excluded. A ``?creator_id=`` request is
    explicit creator-scoped navigation (a store visit), so it is returned even for
    a blocked creator — the web renders the block state; a personal block is not
    existence hiding, unlike the 19+ gate.
    """
    account = resolve_optional_account(request)
    queryset = _public_product_qs(account).order_by("-created_at", "id")
    if creator_id is not None:
        queryset = queryset.filter(creator_id=creator_id)
    else:
        queryset = queryset.exclude(creator_id__in=blocked_creator_ids(account))
    if product_type:
        queryset = queryset.filter(type=product_type)
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return ProductPage(items=[_product_out(p) for p in items], next_cursor=next_cursor)


@products_router.get("/{product_id}", response={200: ProductOut, 404: CommerceError})
def get_product(
    request: HttpRequest, product_id: uuid.UUID
) -> tuple[int, ProductOut | CommerceError]:
    """Return one catalog product by id; 404 if unknown or not publicly visible.

    The web product-detail page consumes this contract. Gating goes through
    :func:`_public_product_qs`, so a draft/hidden/gated-adult product 404s to a
    consumer just like an unknown id (no existence leak).
    """
    product = _public_product_qs(resolve_optional_account(request)).filter(
        id=product_id
    ).first()
    if product is None:
        return 404, CommerceError(
            detail="상품을 찾을 수 없어요.", code=ErrorCode.PRODUCT_NOT_FOUND.value
        )
    return 200, _product_out(product)


api.add_router("/products", products_router)


# --------------------------------------------------------------------------- #
# Studio (owner catalog write; R3 — pure engineering, 법무 무관).
# Owner guard mirrors content.create_post: only the account that operates a
# Creator may manage that creator's catalog, and the scope is always that creator
# (never taken from the body), so a fan cannot touch someone else's products. The
# price is the creator's own display input (NOT a settlement figure — R3 정본).
# --------------------------------------------------------------------------- #
studio_products_router = Router(auth=fan_auth, tags=["studio-commerce"])


class StudioProductOut(Schema):
    """Owner-view product: adds the management fields (status, 19+, timestamps)."""

    id: uuid.UUID
    creator_id: uuid.UUID | None = None
    type: str
    title: str
    price: int
    meta: str
    media_url: str
    description: str
    options: list[str]
    stock: int | None = None
    sold_out: bool
    locked: bool
    status: str
    is_adult: bool
    created_at: datetime


class StudioProductIn(Schema):
    """Owner payload to create a catalog product (display price, not settlement)."""

    type: str
    title: str = Field(min_length=1, max_length=120)
    price: int = Field(default=0, ge=0)
    meta: str = Field(default="", max_length=120)
    media_url: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=2000)
    options: list[str] = Field(default_factory=list)
    stock: int | None = Field(default=None, ge=0)
    sold_out: bool = False
    locked: bool = False
    status: str = ProductStatus.SELLING.value
    is_adult: bool = False

    @field_validator("media_url")
    @classmethod
    def _check_media_url(cls, value: str) -> str:
        """Reject non-http(s) / non-relative media URLs (A5, mirrors content)."""
        return _validated_media_url(value)


class StudioProductPatch(Schema):
    """Owner payload to update a product; only the provided fields are applied."""

    type: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)
    price: int | None = Field(default=None, ge=0)
    meta: str | None = Field(default=None, max_length=120)
    media_url: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    options: list[str] | None = None
    stock: int | None = Field(default=None, ge=0)
    sold_out: bool | None = None
    locked: bool | None = None
    status: str | None = None
    is_adult: bool | None = None

    @field_validator("media_url")
    @classmethod
    def _check_media_url(cls, value: str | None) -> str | None:
        """Validate media_url only when provided (A5, mirrors content)."""
        return None if value is None else _validated_media_url(value)


class StudioAck(Schema):
    """Bare status ack for studio mutations that return no body (delete)."""

    status: str


def _owner_creator(account: Account) -> Creator | None:
    """The creator profile operated by ``account`` (owner guard for studio writes)."""
    return Creator.objects.filter(owner=account).first()


def _studio_product_out(product: Product) -> StudioProductOut:
    """Build the owner-view product response (includes management fields)."""
    return StudioProductOut(
        id=product.id,
        creator_id=product.creator_id,
        type=product.type,
        title=product.title,
        price=product.price,
        meta=product.meta,
        media_url=product.media_url,
        description=product.description,
        options=[str(o) for o in product.options] if isinstance(product.options, list) else [],
        stock=product.stock,
        sold_out=product.sold_out,
        locked=product.locked,
        status=product.status,
        is_adult=product.adult_only,
        created_at=product.created_at,
    )


@studio_products_router.get("", response={200: list[StudioProductOut], 403: CommerceError})
def studio_list_products(
    request: HttpRequest,
) -> tuple[int, list[StudioProductOut] | CommerceError]:
    """List the caller's own creator's products, including draft/hidden and 19+."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    creator = _owner_creator(account)
    if creator is None:
        return 403, CommerceError(
            detail="크리에이터만 상품을 관리할 수 있어요.", code=ErrorCode.OWNER_REQUIRED.value
        )
    products = Product.objects.filter(creator=creator).order_by("-created_at", "id")
    return 200, [_studio_product_out(p) for p in products]


@studio_products_router.post(
    "",
    response={201: StudioProductOut, 403: CommerceError, 422: CommerceError},
    throttle=user_write_throttle("30/min"),
)
def studio_create_product(
    request: HttpRequest, payload: StudioProductIn
) -> tuple[int, StudioProductOut | CommerceError]:
    """Create a product owned by the caller's creator profile; 403 if they operate none."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    creator = _owner_creator(account)
    if creator is None:
        return 403, CommerceError(
            detail="크리에이터만 상품을 관리할 수 있어요.", code=ErrorCode.OWNER_REQUIRED.value
        )
    if payload.type not in ProductType.values:
        return 422, CommerceError(
            detail="상품 유형이 올바르지 않아요.", code=ErrorCode.PRODUCT_TYPE_INVALID.value
        )
    if payload.status not in ProductStatus.values:
        return 422, CommerceError(
            detail="상품 상태가 올바르지 않아요.", code=ErrorCode.PRODUCT_STATUS_INVALID.value
        )
    product = Product.objects.create(
        creator=creator,
        type=payload.type,
        title=payload.title,
        price=payload.price,
        meta=payload.meta,
        media_url=payload.media_url,
        description=payload.description,
        options=payload.options,
        stock=payload.stock,
        sold_out=payload.sold_out,
        locked=payload.locked,
        status=payload.status,
        adult_only=payload.is_adult,
    )
    return 201, _studio_product_out(product)


@studio_products_router.patch(
    "/{product_id}",
    response={200: StudioProductOut, 403: CommerceError, 404: CommerceError, 422: CommerceError},
    throttle=user_write_throttle("30/min"),
)
def studio_update_product(
    request: HttpRequest, product_id: uuid.UUID, payload: StudioProductPatch
) -> tuple[int, StudioProductOut | CommerceError]:
    """Update fields on the caller's own product; 403 (no creator) / 404 (not theirs)."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    creator = _owner_creator(account)
    if creator is None:
        return 403, CommerceError(
            detail="크리에이터만 상품을 관리할 수 있어요.", code=ErrorCode.OWNER_REQUIRED.value
        )
    product = Product.objects.filter(id=product_id, creator=creator).first()
    if product is None:
        return 404, CommerceError(
            detail="상품을 찾을 수 없어요.", code=ErrorCode.PRODUCT_NOT_FOUND.value
        )
    if payload.type is not None:
        if payload.type not in ProductType.values:
            return 422, CommerceError(
                detail="상품 유형이 올바르지 않아요.", code=ErrorCode.PRODUCT_TYPE_INVALID.value
            )
        product.type = payload.type
    if payload.status is not None:
        if payload.status not in ProductStatus.values:
            return 422, CommerceError(
                detail="상품 상태가 올바르지 않아요.", code=ErrorCode.PRODUCT_STATUS_INVALID.value
            )
        product.status = payload.status
    if payload.title is not None:
        product.title = payload.title
    if payload.price is not None:
        product.price = payload.price
    if payload.meta is not None:
        product.meta = payload.meta
    if payload.media_url is not None:
        product.media_url = payload.media_url
    if payload.description is not None:
        product.description = payload.description
    if payload.options is not None:
        product.options = payload.options
    if payload.sold_out is not None:
        product.sold_out = payload.sold_out
    if payload.locked is not None:
        product.locked = payload.locked
    if payload.is_adult is not None:
        product.adult_only = payload.is_adult
    # ``stock`` is nullable (None = untracked), so "omitted" and "set to null" both
    # arrive as None; use the pydantic set-fields marker to patch it only when the
    # client actually sent it.
    if "stock" in payload.model_fields_set:
        product.stock = payload.stock
    product.save()
    return 200, _studio_product_out(product)


@studio_products_router.delete(
    "/{product_id}",
    response={200: StudioAck, 403: CommerceError, 404: CommerceError, 422: CommerceError},
    throttle=user_write_throttle("30/min"),
)
def studio_delete_product(
    request: HttpRequest, product_id: uuid.UUID
) -> tuple[int, StudioAck | CommerceError]:
    """Delete the caller's own product; 403 (no creator) / 404 (not theirs) / 422 (sold).

    A product with order history can't be hard-deleted: ``OrderItem.product`` is
    SET_NULL, so deleting it would sever the historical order lines' attribution
    back to this creator (breaking dashboard/stats counts and order provenance).
    Instead of deleting, the owner should archive it (``status="hidden"``), which
    removes it from public listings while keeping order history intact. A product
    with no order history has nothing to preserve, so it deletes as before.

    Concurrency (F5): the owner check, the reload under ``select_for_update`` and the
    ``order_items`` re-check run in one ``transaction.atomic`` block so the
    check→delete window is narrowed — the product row is locked for the duration, so
    a second concurrent *delete* cannot slip between the check and the delete. NOT a
    complete seal: an in-flight ``create_order`` does not lock the product row, so an
    order committing during this block can still leave a just-deleted product with a
    dangling (SET_NULL) line. Fully closing that needs the order path to lock the
    product too (a broader change deferred), so the residual window is documented,
    not hidden.
    """
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    creator = _owner_creator(account)
    if creator is None:
        return 403, CommerceError(
            detail="크리에이터만 상품을 관리할 수 있어요.", code=ErrorCode.OWNER_REQUIRED.value
        )
    with transaction.atomic():
        product = (
            Product.objects.select_for_update()
            .filter(id=product_id, creator=creator)
            .first()
        )
        if product is None:
            return 404, CommerceError(
                detail="상품을 찾을 수 없어요.", code=ErrorCode.PRODUCT_NOT_FOUND.value
            )
        if product.order_items.exists():
            return 422, CommerceError(
                detail="주문 이력이 있는 상품은 삭제할 수 없어요. 숨김(hidden) 처리해 주세요.",
                code=ErrorCode.PRODUCT_HAS_ORDERS.value,
            )
        product.delete()
    return 200, StudioAck(status="deleted")


api.add_router("/studio/products", studio_products_router)


# --------------------------------------------------------------------------- #
# Orders (fan surface — mock payment, no money moves; B7 gated)
# --------------------------------------------------------------------------- #
class OrderItemOut(Schema):
    """One line of an order (snapshot at purchase; maps to frontend ``OrderItem``)."""

    product_id: uuid.UUID | None = None
    title: str
    type: str
    option: str
    price: int
    qty: int


class OrderRefundOut(Schema):
    """The order's latest refund request, if any (embedded in ``OrderOut``)."""

    status: str
    reason: str


class OrderOut(Schema):
    """A fan's order (maps to the frontend ``Order`` type).

    ``subtotal``/``shipping``/``total`` are display snapshots (shipping is a mock
    ``0`` — no real fulfilment cost is computed). NOT settlement figures.
    """

    id: str
    status: str
    created_at: datetime
    items: list[OrderItemOut]
    subtotal: int
    shipping: int
    total: int
    creator_name: str | None = None
    refund: OrderRefundOut | None = None


class OrderPage(Schema):
    """One page of the fan's orders plus the next cursor."""

    items: list[OrderOut]
    next_cursor: str | None = None


class CreateOrderIn(Schema):
    """Fan payload to place a (mock) order for one product."""

    product_id: uuid.UUID
    qty: int = Field(default=1, ge=1, le=99)
    option: str = Field(default="", max_length=120)
    # Optional idempotency key (B1): a client retry with the same key returns the
    # original order instead of placing a duplicate.
    idempotency_key: str | None = Field(default=None, max_length=64)


class RefundIn(Schema):
    """Fan payload to request a refund against an order."""

    reason: str = Field(min_length=1, max_length=120)
    detail: str = Field(default="", max_length=2000)


def _order_out(order: Order) -> OrderOut:
    """Build the order response from a prefetched order."""
    lines = list(order.items.all())
    subtotal = sum(line.price * line.qty for line in lines)
    # Derive the creator display name from the first line's product (mock orders
    # are single-creator); tolerate a since-deleted product or accountless creator.
    creator_name: str | None = None
    for line in lines:
        product = line.product
        if product is not None and product.creator is not None:
            creator_name = product.creator.name
            break
    refunds = list(order.refund_requests.all())
    refund = (
        OrderRefundOut(status=refunds[0].status, reason=refunds[0].reason)
        if refunds
        else None
    )
    return OrderOut(
        id=order.id,
        status=order.status,
        created_at=order.created_at,
        items=[
            OrderItemOut(
                product_id=line.product_id,
                title=line.title,
                type=line.item_type,
                option=line.option,
                price=line.price,
                qty=line.qty,
            )
            for line in lines
        ],
        subtotal=subtotal,
        shipping=0,
        total=order.total,
        creator_name=creator_name,
        refund=refund,
    )


def _load_order(order_id: str, buyer: Account) -> Order | None:
    """Load the buyer's own order (prefetched), or ``None`` (→ 404, no leak)."""
    return (
        Order.objects.filter(id=order_id, buyer=buyer)
        .prefetch_related("items", "items__product", "items__product__creator", "refund_requests")
        .first()
    )


def _load_order_by_key(buyer: Account, idempotency_key: str) -> Order | None:
    """Load the buyer's order for an idempotency key (prefetched), or ``None`` (B1)."""
    return (
        Order.objects.filter(buyer=buyer, idempotency_key=idempotency_key)
        .prefetch_related("items", "items__product", "items__product__creator", "refund_requests")
        .first()
    )


@orders_router.post(
    "", response={200: OrderOut, 201: OrderOut, 404: CommerceError, 422: CommerceError}
)
def create_order(
    request: HttpRequest, payload: CreateOrderIn
) -> tuple[int, OrderOut | CommerceError]:
    """Place a mock order for one product.

    MOCK: records a ``paid`` order and snapshots the line item, but **no real
    payment is taken and no money moves** (B7 gated). Stock is *validated* but not
    decremented (inventory movement is out of B4 scope).

    Idempotency (B1): if the caller supplies ``idempotency_key`` and already has an
    order for it, the existing order is returned (200) rather than duplicated. The
    order + its line are written in one ``transaction.atomic`` block so a failure
    can never leave a header without its item; the (buyer, key) unique constraint
    closes the concurrent-retry race (both requests pass the pre-check, one insert
    wins, the loser catches ``IntegrityError`` and returns the winner's order). The
    fan notification is sent only *after* the transaction commits, so a rolled-back
    order never emits a stray "order received" notice.
    """
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    if payload.idempotency_key:
        existing = _load_order_by_key(account, payload.idempotency_key)
        if existing is not None:
            return 200, _order_out(existing)
    # Gate through the consumer queryset (draft/hidden and gated-adult excluded), so a
    # draft/hidden/gated-adult product 404s just like an unknown id — the order flow
    # can't be used to buy (or probe the existence of) a listing the fan can't see.
    product = _public_product_qs(account).filter(id=payload.product_id).first()
    if product is None:
        return 404, CommerceError(
            detail="상품을 찾을 수 없어요.", code=ErrorCode.PRODUCT_NOT_FOUND.value
        )
    # Personal-block consistency (F4): the catalog read stays allowed (a personal
    # block is not existence hiding), but placing a new order against a creator this
    # buyer has blocked is refused. One set query, before the stock/state checks.
    if product.creator_id in blocked_creator_ids(account):
        return 422, CommerceError(
            detail="차단한 크리에이터의 콘텐츠에는 상호작용할 수 없어요.",
            code=ErrorCode.INTERACTION_BLOCKED.value,
        )
    # Only a live 'selling' listing is orderable; a 'soldout'-status listing stays
    # publicly visible but cannot be purchased.
    if product.status != ProductStatus.SELLING.value:
        return 422, CommerceError(
            detail="판매 중인 상품이 아니에요.", code=ErrorCode.PRODUCT_NOT_ORDERABLE.value
        )
    if product.locked:
        return 422, CommerceError(
            detail="멤버십 전용 상품이에요.", code=ErrorCode.MEMBERSHIP_ONLY_PRODUCT.value
        )
    if product.sold_out or (product.stock is not None and product.stock <= 0):
        return 422, CommerceError(
            detail="품절된 상품이에요.", code=ErrorCode.OUT_OF_STOCK.value
        )
    if product.stock is not None and payload.qty > product.stock:
        return 422, CommerceError(
            detail="재고가 부족해요.", code=ErrorCode.INSUFFICIENT_STOCK.value
        )

    try:
        with transaction.atomic():
            order = Order.objects.create(
                buyer=account,
                status=OrderStatus.PAID,
                total=product.price * payload.qty,
                idempotency_key=payload.idempotency_key or None,
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                title=product.title,
                item_type=product.type,
                option=payload.option,
                qty=payload.qty,
                price=product.price,
            )
    except IntegrityError:
        # A concurrent retry with the same key won the insert race — return its
        # order instead of surfacing the constraint error.
        if payload.idempotency_key:
            existing = _load_order_by_key(account, payload.idempotency_key)
            if existing is not None:
                return 200, _order_out(existing)
        raise

    notify(
        account,
        NotificationKind.ORDER.value,
        f"'{product.title}' 주문이 접수되었어요.",
        "/orders",
    )
    loaded = _load_order(order.id, account)
    assert loaded is not None  # just created for this buyer
    return 201, _order_out(loaded)


@orders_router.get("", response=OrderPage)
def list_orders(
    request: HttpRequest, cursor: str | None = None, limit: int | None = None
) -> OrderPage:
    """List the requesting fan's own orders, newest first, cursor-paginated."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    queryset = (
        Order.objects.filter(buyer=account)
        .prefetch_related("items", "items__product", "items__product__creator", "refund_requests")
        .order_by("-created_at", "id")
    )
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return OrderPage(items=[_order_out(o) for o in items], next_cursor=next_cursor)


@orders_router.get("/{order_id}", response={200: OrderOut, 404: CommerceError})
def get_order(
    request: HttpRequest, order_id: str
) -> tuple[int, OrderOut | CommerceError]:
    """Return one of the requesting fan's own orders (404 if not theirs)."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    order = _load_order(order_id, account)
    if order is None:
        return 404, CommerceError(
            detail="주문을 찾을 수 없어요.", code=ErrorCode.ORDER_NOT_FOUND.value
        )
    return 200, _order_out(order)


@orders_router.post(
    "/{order_id}/cancel", response={200: OrderOut, 404: CommerceError, 422: CommerceError}
)
def cancel_order(
    request: HttpRequest, order_id: str
) -> tuple[int, OrderOut | CommerceError]:
    """Cancel one of the fan's own orders (only while paid/shipping)."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    order = _load_order(order_id, account)
    if order is None:
        return 404, CommerceError(
            detail="주문을 찾을 수 없어요.", code=ErrorCode.ORDER_NOT_FOUND.value
        )
    if order.status not in _CANCELLABLE:
        return 422, CommerceError(
            detail="취소할 수 없는 주문 상태예요.", code=ErrorCode.ORDER_NOT_CANCELLABLE.value
        )
    order.status = OrderStatus.CANCELLED.value
    order.save(update_fields=["status"])
    return 200, _order_out(order)


@orders_router.post(
    "/{order_id}/refund", response={200: OrderOut, 404: CommerceError, 422: CommerceError}
)
def request_refund(
    request: HttpRequest, order_id: str, payload: RefundIn
) -> tuple[int, OrderOut | CommerceError]:
    """Request a refund against one of the fan's own orders (shipping/completed)."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    order = _load_order(order_id, account)
    if order is None:
        return 404, CommerceError(
            detail="주문을 찾을 수 없어요.", code=ErrorCode.ORDER_NOT_FOUND.value
        )
    if order.status not in _REFUNDABLE:
        return 422, CommerceError(
            detail="환불 신청할 수 없는 주문 상태예요.", code=ErrorCode.ORDER_NOT_REFUNDABLE.value
        )
    # 열린 환불 1건 불변식은 DB 조건부 유니크 제약(uniq_open_refund_per_order)이 봉인 —
    # exists() 선확인은 친절한 메시지용이고, 동시 신청의 패자는 IntegrityError로 잡는다.
    try:
        with transaction.atomic():
            if order.refund_requests.filter(status__in=_OPEN_REFUND).exists():
                return 422, CommerceError(
                    detail="이미 환불 신청이 접수된 주문이에요.",
                    code=ErrorCode.OPEN_REFUND_EXISTS.value,
                )
            RefundRequest.objects.create(
                order=order,
                reason=payload.reason,
                detail=payload.detail,
                status=RefundStatus.REQUESTED,
            )
    except IntegrityError:
        return 422, CommerceError(
            detail="이미 환불 신청이 접수된 주문이에요.", code=ErrorCode.OPEN_REFUND_EXISTS.value
        )
    refreshed = _load_order(order_id, account)
    assert refreshed is not None  # owned above
    return 200, _order_out(refreshed)


api.add_router("/orders", orders_router)
