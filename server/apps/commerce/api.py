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

from django.db import IntegrityError, transaction
from django.http import HttpRequest
from ninja import Router, Schema
from pydantic import Field

from apps.commerce.models import (
    Order,
    OrderItem,
    OrderStatus,
    Product,
    RefundRequest,
    RefundStatus,
)
from apps.identity.auth import fan_auth
from apps.identity.models import Account
from apps.notification.models import NotificationKind
from apps.notification.services import notify
from config.api import api
from config.pagination import paginate

products_router = Router(tags=["commerce"])
orders_router = Router(auth=fan_auth, tags=["commerce-orders"])

# Order states that may still be cancelled / refunded by the fan.
_CANCELLABLE = {OrderStatus.PAID.value, OrderStatus.SHIPPING.value}
_REFUNDABLE = {OrderStatus.SHIPPING.value, OrderStatus.COMPLETED.value}
# Refund states that count as an open request (blocks a second one).
_OPEN_REFUND = {RefundStatus.REQUESTED.value, RefundStatus.REVIEWING.value}


class CommerceError(Schema):
    """Stable error shape for commerce endpoints."""

    detail: str


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
    queryset = Product.objects.select_related("creator").order_by("-created_at", "id")
    if creator_id is not None:
        queryset = queryset.filter(creator_id=creator_id)
    if product_type:
        queryset = queryset.filter(type=product_type)
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return ProductPage(items=[_product_out(p) for p in items], next_cursor=next_cursor)


@products_router.get("/{product_id}", response={200: ProductOut, 404: CommerceError})
def get_product(
    request: HttpRequest, product_id: uuid.UUID
) -> tuple[int, ProductOut | CommerceError]:
    """Return one catalog product by id; 404 if unknown (B5).

    The web product-detail page consumes this contract. ``creator`` is
    ``select_related`` so the owning creator name is served without an extra query.
    """
    del request
    product = Product.objects.select_related("creator").filter(id=product_id).first()
    if product is None:
        return 404, CommerceError(detail="상품을 찾을 수 없어요.")
    return 200, _product_out(product)


api.add_router("/products", products_router)


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
    product = Product.objects.select_related("creator").filter(id=payload.product_id).first()
    if product is None:
        return 404, CommerceError(detail="상품을 찾을 수 없어요.")
    if product.locked:
        return 422, CommerceError(detail="멤버십 전용 상품이에요.")
    if product.sold_out or (product.stock is not None and product.stock <= 0):
        return 422, CommerceError(detail="품절된 상품이에요.")
    if product.stock is not None and payload.qty > product.stock:
        return 422, CommerceError(detail="재고가 부족해요.")

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
        return 404, CommerceError(detail="주문을 찾을 수 없어요.")
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
        return 404, CommerceError(detail="주문을 찾을 수 없어요.")
    if order.status not in _CANCELLABLE:
        return 422, CommerceError(detail="취소할 수 없는 주문 상태예요.")
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
        return 404, CommerceError(detail="주문을 찾을 수 없어요.")
    if order.status not in _REFUNDABLE:
        return 422, CommerceError(detail="환불 신청할 수 없는 주문 상태예요.")
    # 열린 환불 1건 불변식은 DB 조건부 유니크 제약(uniq_open_refund_per_order)이 봉인 —
    # exists() 선확인은 친절한 메시지용이고, 동시 신청의 패자는 IntegrityError로 잡는다.
    try:
        with transaction.atomic():
            if order.refund_requests.filter(status__in=_OPEN_REFUND).exists():
                return 422, CommerceError(detail="이미 환불 신청이 접수된 주문이에요.")
            RefundRequest.objects.create(
                order=order,
                reason=payload.reason,
                detail=payload.detail,
                status=RefundStatus.REQUESTED,
            )
    except IntegrityError:
        return 422, CommerceError(detail="이미 환불 신청이 접수된 주문이에요.")
    refreshed = _load_order(order_id, account)
    assert refreshed is not None  # owned above
    return 200, _order_out(refreshed)


api.add_router("/orders", orders_router)
