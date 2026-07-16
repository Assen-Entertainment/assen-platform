"""Commerce API — product catalog (read) + mock order flow (SDLC 09 §4, B2·B4).

The product listing is read-only. B4 adds a fan order flow (``fan_auth``): place a
**mock** order (no real payment; no money moves — B7 gated), list/read one's own
orders, cancel, and request a refund. Filter the catalog to a creator via
``?creator_id=`` and to a kind via ``?product_type=``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F, Q, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router, Schema
from pydantic import Field, field_validator

from apps.admin_rbac.permissions import has_min_role, operator_required
from apps.audit.models import AuditAction
from apps.audit.services import record_audit
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
from apps.identity.auth import authed, fan_auth, resolve_optional_account
from apps.identity.models import Account, Role
from apps.membership.services import active_subscription
from apps.notification.models import NotificationKind
from apps.notification.services import notify
from apps.payments.models import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentProvider,
    PaymentReversalStatus,
)
from apps.payments.services import (
    record_free_grant,
    record_mock_reversal,
    record_mock_settlement,
)
from apps.social.models import blocked_creator_ids
from config.api import api
from config.errors import ApiError, ErrorCode
from config.pagination import paginate
from config.patch import apply_optional
from config.payment import (
    ChargeStatus,
    PaymentCharge,
    PaymentProvenance,
    PaymentRefund,
    PricingKind,
    payment_gateway,
    require_payment_available,
)
from config.throttle import user_write_throttle

# Money-path observability (order/refund lifecycle). Structured, PII-free: only
# ids/codes/status and mock (non-settlement) amounts are logged — never a name,
# phone, or address (those live on the order but must not reach the log stream).
logger = logging.getLogger(__name__)


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
    # 스토어 카드→크리에이터 프로필 링크용 핸들(전역 카탈로그 상품은 빈 문자열).
    creator_handle: str = ""
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
    # Explicit price intent (ASS-297): "free" offerings are acquired via /orders/free,
    # not the paid checkout. Default "paid" (a price-0 row is a placeholder).
    pricing_kind: str = PricingKind.PAID.value


class ProductPage(Schema):
    """One page of products plus the next cursor."""

    items: list[ProductOut]
    next_cursor: str | None = None


def _product_out(product: Product) -> ProductOut:
    """Build the product response."""
    return ProductOut(
        id=product.id,
        creator_id=product.creator_id,
        # 상세/카드 표기용 소유 크리에이터명·핸들(전역 카탈로그 상품은 빈 문자열).
        creator_name=product.creator.name if product.creator is not None else "",
        creator_handle=product.creator.handle if product.creator is not None else "",
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
        pricing_kind=product.pricing_kind,
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
    """Owner-view product: adds the management fields (status, 19+, timestamps).

    ``sold`` is the total quantity sold via **non-cancelled** orders (ASS-264) — a
    count, never a settlement/revenue figure (PG·재무 게이트 후행).
    """

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
    sold: int
    # Explicit price intent (ASS-297): mirrors the fan-facing ProductOut so the owner
    # studio can read/set whether an offering is genuinely free vs a price-0 paid row.
    pricing_kind: str = PricingKind.PAID.value


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
    pricing_kind: str = PricingKind.PAID.value

    @field_validator("media_url")
    @classmethod
    def _check_media_url(cls, value: str) -> str:
        """Reject non-http(s) / non-relative media URLs (A5, mirrors content)."""
        return _validated_media_url(value)

    @field_validator("pricing_kind")
    @classmethod
    def _check_pricing_kind(cls, value: str) -> str:
        """Reject a pricing_kind outside the known choices (ASS-297 → 422)."""
        if value not in PricingKind.values:
            raise ValueError("pricing_kind must be 'paid' or 'free'.")
        return value


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
    pricing_kind: str | None = None

    @field_validator("media_url")
    @classmethod
    def _check_media_url(cls, value: str | None) -> str | None:
        """Validate media_url only when provided (A5, mirrors content)."""
        return None if value is None else _validated_media_url(value)

    @field_validator("pricing_kind")
    @classmethod
    def _check_pricing_kind(cls, value: str | None) -> str | None:
        """Validate pricing_kind only when provided (ASS-297 → 422)."""
        if value is not None and value not in PricingKind.values:
            raise ValueError("pricing_kind must be 'paid' or 'free'.")
        return value


class StudioAck(Schema):
    """Bare status ack for studio mutations that return no body (delete)."""

    status: str


def _owner_creator(account: Account) -> Creator | None:
    """The creator profile operated by ``account`` (owner guard for studio writes)."""
    return Creator.objects.filter(owner=account).first()


def _product_sold(product: Product) -> int:
    """Total quantity sold for ``product`` via non-cancelled orders (ASS-264).

    ``studio_list_products`` annotates ``sold_count`` on the whole queryset in one
    aggregate query (no N+1); this falls back to a single live aggregate for the
    lone-product create/update responses, where the value was never annotated. A
    cancelled order never happened commercially, so its lines are excluded — same
    invariant as ``studio_stats``' order count. Count only, never a revenue figure.
    """
    annotated = getattr(product, "sold_count", None)
    if annotated is not None:
        return int(annotated)
    total = (
        OrderItem.objects.filter(product=product)
        .exclude(order__status=OrderStatus.CANCELLED.value)
        .aggregate(total=Coalesce(Sum("qty"), 0))["total"]
    )
    return int(total)


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
        sold=_product_sold(product),
        pricing_kind=product.pricing_kind,
    )


@studio_products_router.get("", response={200: list[StudioProductOut], 403: CommerceError})
def studio_list_products(
    request: HttpRequest,
) -> tuple[int, list[StudioProductOut] | CommerceError]:
    """List the caller's own creator's products, including draft/hidden and 19+."""
    account = authed(request)
    creator = _owner_creator(account)
    if creator is None:
        return 403, CommerceError(
            detail="크리에이터만 상품을 관리할 수 있어요.", code=ErrorCode.OWNER_REQUIRED.value
        )
    # sold_count: total qty sold per product via one aggregate query (no N+1) — the
    # OrderItem->Product join is a single relation, so unlike the creator followers/
    # posts case there is no cross-relation fan-out to guard against.
    products = (
        Product.objects.filter(creator=creator)
        .annotate(
            sold_count=Coalesce(
                Sum(
                    "order_items__qty",
                    filter=~Q(order_items__order__status=OrderStatus.CANCELLED.value),
                ),
                0,
            )
        )
        .order_by("-created_at", "id")
    )
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
    account = authed(request)
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
    # Coherence guard (ASS-297): a genuinely free offering must carry a zero price —
    # "free" and a nonzero price are mutually exclusive, else the free-grant path
    # would silently ignore a stated price.
    if payload.pricing_kind == PricingKind.FREE.value and payload.price != 0:
        return 422, CommerceError(
            detail="무료 상품의 가격은 0이어야 해요.",
            code=ErrorCode.PRICING_FREE_REQUIRES_ZERO_PRICE.value,
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
        pricing_kind=payload.pricing_kind,
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
    account = authed(request)
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
    # Coherence guard on the EFFECTIVE post-patch values (ASS-297): a patch may set
    # either field, so compute what the row would become and reject a free offering
    # left with a nonzero price (whether the price or the kind was the one changed).
    effective_kind = (
        payload.pricing_kind if payload.pricing_kind is not None else product.pricing_kind
    )
    effective_price = payload.price if payload.price is not None else product.price
    if effective_kind == PricingKind.FREE.value and effective_price != 0:
        return 422, CommerceError(
            detail="무료 상품의 가격은 0이어야 해요.",
            code=ErrorCode.PRICING_FREE_REQUIRES_ZERO_PRICE.value,
        )
    apply_optional(
        product,
        payload,
        [
            "title", "price", "meta", "media_url", "description", "options",
            "sold_out", "locked", "pricing_kind",
        ],
    )
    # ``is_adult`` maps to a differently-named model field (``adult_only``), so it
    # stays inline rather than going through the same-name apply_optional pass.
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
    account = authed(request)
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


class OrderShippingOut(Schema):
    """Delivery-address snapshot echoed on a physical (goods) order (own orders only)."""

    recipient_name: str
    recipient_phone: str
    postal_code: str
    address1: str
    address2: str


class OrderTrackingOut(Schema):
    """Shipment tracking echoed once a physical order has been shipped (#11).

    Populated by the creator/operator at ``/orders/{id}/ship``; ``None`` on an order
    that has not shipped (still PAID, or a digital order completed without shipping).
    Mirrors the web ``Order.tracking`` shape (``{carrier, number}``) — carrier name
    and tracking number only, no PII.
    """

    carrier: str
    number: str


class OrderOut(Schema):
    """A fan's order row (maps to the frontend ``Order`` type).

    ``subtotal``/``shipping``/``shipping_fee``/``total`` are display snapshots
    computed server-side (``total = subtotal + shipping_fee``; shipping is a mock
    ``0`` until the fee policy is set). NOT settlement figures. ``shipping`` and
    ``shipping_fee`` carry the same value — ``shipping`` is the pre-existing field
    the web consumes; ``shipping_fee`` is the explicit alias matching the model.

    Deliberately carries **no delivery address** (ASS-291 A-3): the shipping
    snapshot (recipient name / phone / postal / street) is PII, and the orders
    *list* must not echo it in every row. It is exposed only on the owner-scoped
    single-order responses via :class:`OrderDetailOut`.
    """

    id: str
    status: str
    created_at: datetime
    items: list[OrderItemOut]
    subtotal: int
    shipping: int
    shipping_fee: int
    total: int
    creator_name: str | None = None
    refund: OrderRefundOut | None = None
    # Shipment tracking once the order has shipped (#11); ``None`` until then. Carrier
    # + number only (no PII), so it is safe on the list as well as the detail.
    tracking: OrderTrackingOut | None = None


class OrderDetailOut(OrderOut):
    """A single order returned to its owner, extended with the delivery snapshot.

    Used only by the owner-scoped single-order responses (detail read, place,
    cancel, refund) — never the list — so ``shipping_address`` (a goods order's
    recipient name / phone / postal / street PII) reaches a fan only for their own
    order, one at a time, not enumerated across a paginated list (ASS-291 A-3).
    ``None`` for an order that needs no address (digital/experience/ticket/coupon).
    """

    shipping_address: OrderShippingOut | None = None


class OrderPage(Schema):
    """One page of the fan's orders plus the next cursor (no addresses — A-3)."""

    items: list[OrderOut]
    next_cursor: str | None = None


class ShippingIn(Schema):
    """Delivery address for a physical (goods) order (required for ``type=goods``)."""

    recipient_name: str = Field(default="", max_length=60)
    recipient_phone: str = Field(default="", max_length=32)
    postal_code: str = Field(default="", max_length=16)
    address1: str = Field(default="", max_length=200)
    address2: str = Field(default="", max_length=200)


class CreateOrderIn(Schema):
    """Fan payload to place a (mock) order for one product."""

    product_id: uuid.UUID
    qty: int = Field(default=1, ge=1, le=99)
    option: str = Field(default="", max_length=120)
    # Delivery address — required for physical (goods) orders, ignored otherwise.
    shipping: ShippingIn | None = None
    # Optional idempotency key (B1): a client retry with the same key returns the
    # original order instead of placing a duplicate.
    idempotency_key: str | None = Field(default=None, max_length=64)


def _shipping_is_complete(shipping: ShippingIn | None) -> bool:
    """Whether ``shipping`` carries the fields a physical delivery needs.

    ``address2`` (detail line) is optional; the recipient, phone, postal code, and
    the first address line are required so a goods order cannot be placed with an
    empty/partial address that could not actually be fulfilled.
    """
    if shipping is None:
        return False
    return all(
        bool(value.strip())
        for value in (
            shipping.recipient_name,
            shipping.recipient_phone,
            shipping.postal_code,
            shipping.address1,
        )
    )


class RefundIn(Schema):
    """Fan payload to request a refund against an order."""

    reason: str = Field(min_length=1, max_length=120)
    detail: str = Field(default="", max_length=2000)


def _order_common_fields(order: Order) -> dict[str, Any]:
    """Shared, address-free fields for both the list row and the detail response."""
    lines = list(order.items.all())
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
    tracking = (
        OrderTrackingOut(carrier=order.tracking_carrier, number=order.tracking_number)
        if order.tracking_carrier or order.tracking_number
        else None
    )
    return {
        "id": order.id,
        "status": order.status,
        "created_at": order.created_at,
        "items": [
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
        "subtotal": order.subtotal,
        "shipping": order.shipping_fee,
        "shipping_fee": order.shipping_fee,
        "total": order.total,
        "creator_name": creator_name,
        "refund": refund,
        "tracking": tracking,
    }


def _order_out(order: Order) -> OrderOut:
    """Build an address-free order row (the list response — A-3, no shipping PII)."""
    return OrderOut(**_order_common_fields(order))


def _order_detail_out(order: Order) -> OrderDetailOut:
    """Build the owner-scoped single-order response, including the delivery snapshot.

    Echoes the delivery snapshot only when one was captured (goods orders); a
    digital/experience/ticket/coupon order has an empty recipient → ``None``. This
    address is exposed here (one own order at a time), never on the list (A-3).
    """
    shipping_address = (
        OrderShippingOut(
            recipient_name=order.recipient_name,
            recipient_phone=order.recipient_phone,
            postal_code=order.postal_code,
            address1=order.address1,
            address2=order.address2,
        )
        if order.recipient_name
        else None
    )
    return OrderDetailOut(**_order_common_fields(order), shipping_address=shipping_address)


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


def _restock_order_lines(order: Order) -> None:
    """Restore stock for each stock-tracked line of a cancelled/refunded order.

    Winner-only contract: call this exactly once, and only after the caller's own
    conditional status UPDATE won the transition race (rowcount == 1), so stock can
    never be double-restored (F-A). The two-step restore mirrors ``create_order``'s
    sell-out: a product that auto sold-out (stock hit 0) is re-opened (``sold_out``
    cleared) on restore, while a product an owner manually marked ``sold_out`` with
    stock still remaining keeps that flag (F-F) — the restore adds the unit back but
    does not silently re-open a listing the owner paused. A since-deleted product
    line (SET_NULL) has nothing to restore and is skipped. Shared by the fan cancel
    and the operator refund-accept paths so the restock invariant is identical.
    """
    for line in order.items.all():
        product = line.product
        if product is not None and product.stock is not None:
            reopened = Product.objects.filter(id=product.id, stock=0).update(
                stock=F("stock") + line.qty, sold_out=False
            )
            if reopened == 0:
                Product.objects.filter(id=product.id).update(stock=F("stock") + line.qty)


def _reverse_settled_order(order: Order, *, reason: str) -> None:
    """Durably record a reversal (void/refund) of an order's original capture (#3).

    The BLOCKER-seam: a fan cancel / operator refund-accept cancels + restocks the
    order while money never actually moves (mock). This routes that reversal through
    the gateway's (mock) void/refund op and writes an append-only
    :class:`~apps.payments.models.PaymentReversal` tied to the settlement it reverses,
    so when a real PG capture is later added the reversal has a durable record to
    reconcile — the API no longer tells a fan "refunded" while the capture stays
    settled with nothing recorded.

    Winner-only + idempotent: call this exactly once, inside the caller's transaction,
    after its conditional status UPDATE won the cancel/refund race. It only reverses a
    real capture — a succeeded MOCK settlement attempt for the order (a free grant or
    an unsettled order has nothing to reverse and is skipped) — and no-ops if that
    attempt already carries a succeeded reversal, so a second cancel/refund-accept can
    never double-record. The gateway outcome drives the persisted status (succeeded on
    approve, failed on decline); a gateway error fails the reversal closed (recorded
    failed) without unwinding the committed cancel/restock.
    """
    attempt = (
        PaymentAttempt.objects.filter(
            order=order,
            provider=PaymentProvider.MOCK.value,
            status=PaymentAttemptStatus.SUCCEEDED.value,
        )
        .order_by("-created_at")
        .first()
    )
    if attempt is None:
        # No real capture to reverse (free grant / unsettled order): nothing to record.
        return
    if attempt.reversals.filter(status=PaymentReversalStatus.SUCCEEDED.value).exists():
        # Idempotency guard on the attempt: the capture was already reversed (a racing
        # cancel/refund-accept won first), so a second call must not double-record.
        return
    gateway = payment_gateway()
    if gateway is None:
        # A mock settlement exists but no gateway is wired now (mock disabled since):
        # still record the owed reversal as PENDING so it is not silently lost.
        refund = PaymentRefund(
            status=ChargeStatus.PENDING,
            reversal_ref="",
            provenance=PaymentProvenance.MOCK,
        )
    else:
        try:
            refund = gateway.refund(
                order_id=str(order.id),
                amount=order.total,
                currency="KRW",
                original_ref=order.payment_ref,
                idempotency_key=order.idempotency_key or None,
            )
        except Exception:  # noqa: BLE001 — a gateway error fails the reversal closed
            logger.warning(
                "commerce.reversal.gateway_error",
                extra={"order_id": order.id},
                exc_info=True,
            )
            refund = PaymentRefund(
                status=ChargeStatus.FAILED,
                reversal_ref="",
                provenance=PaymentProvenance.MOCK,
            )
    reversal = record_mock_reversal(
        original_attempt=attempt, refund=refund, amount=order.total, reason=reason
    )
    logger.info(
        "commerce.reversal.recorded",
        extra={
            "order_id": order.id,
            "attempt_id": str(attempt.id),
            "reversal_id": str(reversal.id),
            "status": reversal.status,
        },
    )


@orders_router.post(
    "", response={200: OrderDetailOut, 201: OrderDetailOut, 404: CommerceError, 422: CommerceError},
    throttle=user_write_throttle("20/min"),
)
def create_order(
    request: HttpRequest, payload: CreateOrderIn
) -> tuple[int, OrderDetailOut | CommerceError]:
    """Place a mock order for one product via a 2-phase payment intent (#4/#2).

    MOCK: the deterministic mock captures synchronously and approves, so the endpoint
    still returns a ``paid`` order and snapshots the line item, but **no real payment
    is taken and no money moves** (B7 gated). The order amounts
    (``subtotal``/``shipping_fee``/``total``, ``total = subtotal + shipping_fee``)
    are computed server-side so the fan is charged exactly what is shown; shipping
    is a fixed mock ``0`` until the fee policy is set (대표·재무 게이트). A physical
    (``goods``) order must carry a delivery address, else 422.

    Two-phase structure (#4/#2 seam — so a real PG plugs in without a lost charge):

    * **PHASE 1 (``transaction.atomic``, then COMMIT):** reserve stock with the
      ``stock >= qty`` conditional UPDATE (0 rows = a concurrent buyer took the last
      unit → 422; the last unit flips ``sold_out``), then persist the order as
      **PENDING** with its line. NO gateway call and NO settlement happen inside this
      transaction, so a capture that succeeds after a DB-commit failure can never
      charge a customer with no order — the durable order exists first.
    * **PHASE 2 (OUTSIDE the transaction):** capture through the gateway (idempotent —
      the order's key is passed so a real PG dedups a retry). On approval, a SECOND
      short transaction flips PENDING→PAID (conditional-UPDATE rowcount gate) and
      ledgers the settlement. On decline/error, PENDING→FAILED and the reserved stock
      is restored (mirrors ``cancel_order``), and the fan gets a coded 402 — never a
      leaked stock unit or a silent stuck-pending order.

    Idempotency (B1): if the caller supplies ``idempotency_key`` and already has an
    order for it, the existing order is returned (200) rather than duplicated —
    PENDING if a capture is still in flight, PAID once settled, so a retry never
    double-charges or double-orders. The (buyer, key) unique constraint closes the
    concurrent-retry race in PHASE 1 (both requests pass the pre-check, one insert
    wins, the loser catches ``IntegrityError`` — which also rolls back its decrement —
    and returns the winner's order). The fan notification is sent only *after*
    PENDING→PAID, so a PENDING/FAILED order never emits a stray "order received" notice.
    """
    account = authed(request)
    # Fail closed before ANY side effect — including the idempotency replay below:
    # with no real PG and the mock off, an order must never become PAID (ASS-286).
    require_payment_available()
    if payload.idempotency_key:
        existing = _load_order_by_key(account, payload.idempotency_key)
        if existing is not None:
            return 200, _order_detail_out(existing)
    # Gate through the consumer queryset (draft/hidden and gated-adult excluded), so a
    # draft/hidden/gated-adult product 404s just like an unknown id — the order flow
    # can't be used to buy (or probe the existence of) a listing the fan can't see.
    product = _public_product_qs(account).filter(id=payload.product_id).first()
    if product is None:
        return 404, CommerceError(
            detail="상품을 찾을 수 없어요.", code=ErrorCode.PRODUCT_NOT_FOUND.value
        )
    # A free offering is acquired only via the dedicated free-grant path (/orders/
    # free), never the paid checkout — this keeps require_payment_available() an
    # unconditional head-guard and stops a free item minting a mock/external
    # settlement (ASS-297).
    if product.pricing_kind == PricingKind.FREE:
        return 422, CommerceError(
            detail="무료 상품은 '무료로 받기'로 신청해 주세요.",
            code=ErrorCode.PRICING_IS_FREE.value,
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
    # A locked product is membership-gated: orderable only by an active subscriber of
    # the product's creator (server-authoritative entitlement). A non-subscriber (or a
    # creatorless locked product, which has no subscribable creator) is refused 422.
    if product.locked and active_subscription(account, product.creator) is None:
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
    # A physical (goods) order needs a delivery address; digital/experience/ticket/
    # coupon orders need none. Checked last so the existing gating errors above keep
    # their codes. (실운영 전 개인정보 처리방침에 배송지 항목 반영 필요 — 법무 확인;
    # 계약·mock 흐름은 무게이트.)
    # Delivery checkout is gated off until the postal-shipping privacy policy is
    # approved (ASS-287 A-1). A physical (goods) order collects a recipient
    # name/phone/address, so refuse it while off — no shipping PII is collected.
    # (Non-goods orders carry no address and are unaffected.)
    if product.type == ProductType.GOODS.value and not settings.ENABLE_SHIPPING_CHECKOUT:
        raise ApiError(
            503,
            "배송 결제가 아직 준비되지 않았어요.",
            code=ErrorCode.SHIPPING_CHECKOUT_UNAVAILABLE,
        )
    if product.type == ProductType.GOODS.value and not _shipping_is_complete(
        payload.shipping
    ):
        return 422, CommerceError(
            detail="배송지를 입력해 주세요.",
            code=ErrorCode.SHIPPING_ADDRESS_REQUIRED.value,
        )

    # Server-authoritative amount snapshot (display only; NOT settlement — B7).
    subtotal = product.price * payload.qty
    shipping_fee = 0  # 배송비 정책 확정 전 0 — 정책은 대표·재무 게이트
    total = subtotal + shipping_fee
    # Snapshot the delivery address only for a physical (goods) order — a
    # digital/experience/ticket/coupon order needs none, so any address the client
    # sent is dropped (matches the "ignored otherwise" contract, F-G). Each field is
    # trimmed so surrounding whitespace is never persisted.
    ship = payload.shipping
    if product.type == ProductType.GOODS.value and ship is not None:
        shipping_snapshot = {
            "recipient_name": ship.recipient_name.strip(),
            "recipient_phone": ship.recipient_phone.strip(),
            "postal_code": ship.postal_code.strip(),
            "address1": ship.address1.strip(),
            "address2": ship.address2.strip(),
        }
    else:
        shipping_snapshot = {
            "recipient_name": "",
            "recipient_phone": "",
            "postal_code": "",
            "address1": "",
            "address2": "",
        }

    # --- PHASE 1 — persist a PENDING order (stock reserved), then COMMIT. ------ #
    # No gateway call and no settlement run inside this transaction: the durable
    # order must exist BEFORE any capture, so a real PG charge that succeeds after a
    # DB-commit failure can never bill a customer with no order (#4/#2 seam).
    try:
        with transaction.atomic():
            # Atomic stock guard: decrement only while at least ``qty`` remains, so
            # two concurrent buyers cannot oversell the last unit. 0 rows updated =
            # a racing order won it → 422 (the empty transaction commits nothing).
            if product.stock is not None:
                deducted = Product.objects.filter(
                    id=product.id, stock__gte=payload.qty
                ).update(stock=F("stock") - payload.qty)
                if deducted == 0:
                    # A concurrent retry with the same idempotency key may have
                    # already placed this exact order and consumed the unit — return
                    # it instead of a spurious out-of-stock 422 (code review minor1).
                    if payload.idempotency_key:
                        existing = _load_order_by_key(account, payload.idempotency_key)
                        if existing is not None:
                            return 200, _order_detail_out(existing)
                    return 422, CommerceError(
                        detail="재고가 부족해요.",
                        code=ErrorCode.INSUFFICIENT_STOCK.value,
                    )
                # Reflect the last-unit sell-out on the order-flow flag.
                Product.objects.filter(id=product.id, stock=0).update(sold_out=True)
            order = Order.objects.create(
                buyer=account,
                status=OrderStatus.PENDING,
                subtotal=subtotal,
                shipping_fee=shipping_fee,
                total=total,
                idempotency_key=payload.idempotency_key or None,
                # Intended settlement rail: require_payment_available() above already
                # guaranteed the mock is wired, so the order is created against it and
                # the PHASE-2 capture confirms it (never guessed — ASS-298).
                payment_provenance=PaymentProvenance.MOCK,
                **shipping_snapshot,
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
        # order instead of surfacing the constraint error. The loser's stock
        # decrement rolls back with this transaction, so the winner holds the only
        # reservation (no double-decrement, no double-order).
        if payload.idempotency_key:
            existing = _load_order_by_key(account, payload.idempotency_key)
            if existing is not None:
                return 200, _order_detail_out(existing)
        raise

    # --- PHASE 2 — capture OUTSIDE the DB transaction (idempotent). ------------ #
    # The order is already durable (PENDING), so a capture that commits even as this
    # request dies leaves a recoverable PENDING order — never a charge with no order.
    # The order's idempotency key is passed through so a real PG dedups a retried
    # capture. The mock approves inline; a real PG (포트원/토스) plugs in here.
    gateway = payment_gateway()
    charge: PaymentCharge | None = None
    if gateway is not None:
        try:
            charge = gateway.charge(
                order_id=str(order.id),
                amount=total,
                currency="KRW",
                idempotency_key=payload.idempotency_key or None,
            )
        except Exception:  # noqa: BLE001 — any gateway error fails the order closed (declined)
            logger.warning(
                "commerce.order.charge_error",
                extra={"order_id": order.id},
                exc_info=True,
            )
            charge = None

    if charge is None or not charge.approved:
        # Decline (or gateway error / no gateway): PENDING→FAILED and RESTORE the
        # reserved stock so a failed checkout never leaks stock. The conditional-
        # UPDATE rowcount gate makes the restock single-winner (mirrors cancel_order);
        # the block commits BEFORE the raise so the FAILED state + restock persist.
        with transaction.atomic():
            failed = Order.objects.filter(
                id=order.id, status=OrderStatus.PENDING.value
            ).update(status=OrderStatus.FAILED.value, failed_at=timezone.now())
            if failed:
                _restock_order_lines(order)
        logger.warning(
            "commerce.order.payment_declined",
            extra={"order_id": order.id, "buyer_id": str(account.fan_id)},
        )
        raise ApiError(
            402,
            "결제가 거절되었어요. 다시 시도해 주세요.",
            code=ErrorCode.PAYMENT_DECLINED,
        )

    # Approved: transition PENDING→PAID and ledger the settlement in a SECOND short
    # transaction. The conditional-UPDATE rowcount gate makes this single-winner, so a
    # retry can never double-settle; ``payment_ref`` records the gateway's transaction
    # reference (a mock id today, a real PG's ref when wired).
    settled = False
    with transaction.atomic():
        paid = Order.objects.filter(
            id=order.id, status=OrderStatus.PENDING.value
        ).update(
            status=OrderStatus.PAID.value,
            paid_at=timezone.now(),
            payment_ref=charge.provider_ref,
        )
        if paid:
            record_mock_settlement(
                order=order,
                amount=total,
                idempotency_key=payload.idempotency_key or None,
            )
            settled = True

    if settled:
        # Notify only when THIS request won the PENDING→PAID transition — a
        # PENDING/FAILED order (or a concurrent retry that lost the gate) never emits
        # a stray "order received" notice.
        try:
            notify(
                account,
                NotificationKind.ORDER.value,
                f"'{product.title}' 주문이 접수되었어요.",
                "/orders",
            )
        except Exception:  # noqa: BLE001 — a committed order must not 500 on a notification failure
            logger.warning(
                "commerce.order.notify_failed",
                extra={"order_id": order.id},
                exc_info=True,
            )
    logger.info(
        "commerce.order.created",
        extra={
            "order_id": order.id,
            "buyer_id": str(account.fan_id),
            "product_id": str(product.id),
            "qty": payload.qty,
            "total": total,
        },
    )
    loaded = _load_order(order.id, account)
    assert loaded is not None  # just created for this buyer
    return 201, _order_detail_out(loaded)


@orders_router.post(
    "/free",
    response={
        200: OrderDetailOut,
        201: OrderDetailOut,
        404: CommerceError,
        422: CommerceError,
    },
    throttle=user_write_throttle("20/min"),
)
def create_free_order(
    request: HttpRequest, payload: CreateOrderIn
) -> tuple[int, OrderDetailOut | CommerceError]:
    """Acquire an explicitly free product — no payment, provenance=free (ASS-297).

    The ONLY way to obtain a ``pricing_kind=free`` product: the paid checkout
    refuses it (``PricingIsFree``) and this path refuses a paid product
    (``PricingNotFree``), so a price-0 placeholder can never be taken for free.
    Every non-payment gate the paid path enforces still applies — visibility,
    personal block, sell-out/stock, and (for goods) the shipping-checkout gate and
    a complete delivery address — so "free" drops only the payment requirement, not
    the shipping-PII or availability guards. Amounts are forced to 0 and a FREE
    ``PaymentAttempt`` is ledgered exactly like a paid settlement.
    """
    account = authed(request)
    # No require_payment_available() — a free grant settles nothing. Idempotency
    # still applies so a retried grant returns the original instead of duplicating.
    if payload.idempotency_key:
        existing = _load_order_by_key(account, payload.idempotency_key)
        if existing is not None:
            return 200, _order_detail_out(existing)
    product = _public_product_qs(account).filter(id=payload.product_id).first()
    if product is None:
        return 404, CommerceError(
            detail="상품을 찾을 수 없어요.", code=ErrorCode.PRODUCT_NOT_FOUND.value
        )
    # Only an explicitly free offering may be acquired here — a paid product (incl.
    # a price-0 placeholder) must go through the normal, payment-gated path.
    if product.pricing_kind != PricingKind.FREE:
        return 422, CommerceError(
            detail="무료로 받을 수 있는 상품이 아니에요.",
            code=ErrorCode.PRICING_NOT_FREE.value,
        )
    if product.creator_id in blocked_creator_ids(account):
        return 422, CommerceError(
            detail="차단한 크리에이터의 콘텐츠에는 상호작용할 수 없어요.",
            code=ErrorCode.INTERACTION_BLOCKED.value,
        )
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
    # Free goods still pass the shipping gate SEPARATELY (ASS-297): the payment gate
    # is dropped, the shipping-PII / delivery-address gate is not.
    if product.type == ProductType.GOODS.value and not settings.ENABLE_SHIPPING_CHECKOUT:
        raise ApiError(
            503,
            "배송 결제가 아직 준비되지 않았어요.",
            code=ErrorCode.SHIPPING_CHECKOUT_UNAVAILABLE,
        )
    if product.type == ProductType.GOODS.value and not _shipping_is_complete(
        payload.shipping
    ):
        return 422, CommerceError(
            detail="배송지를 입력해 주세요.",
            code=ErrorCode.SHIPPING_ADDRESS_REQUIRED.value,
        )
    ship = payload.shipping
    if product.type == ProductType.GOODS.value and ship is not None:
        shipping_snapshot = {
            "recipient_name": ship.recipient_name.strip(),
            "recipient_phone": ship.recipient_phone.strip(),
            "postal_code": ship.postal_code.strip(),
            "address1": ship.address1.strip(),
            "address2": ship.address2.strip(),
        }
    else:
        shipping_snapshot = {
            "recipient_name": "",
            "recipient_phone": "",
            "postal_code": "",
            "address1": "",
            "address2": "",
        }
    try:
        with transaction.atomic():
            if product.stock is not None:
                deducted = Product.objects.filter(
                    id=product.id, stock__gte=payload.qty
                ).update(stock=F("stock") - payload.qty)
                if deducted == 0:
                    if payload.idempotency_key:
                        existing = _load_order_by_key(
                            account, payload.idempotency_key
                        )
                        if existing is not None:
                            return 200, _order_detail_out(existing)
                    return 422, CommerceError(
                        detail="재고가 부족해요.",
                        code=ErrorCode.INSUFFICIENT_STOCK.value,
                    )
                Product.objects.filter(id=product.id, stock=0).update(sold_out=True)
            # A free grant is a settled order at amount 0, tagged FREE provenance.
            order = Order.objects.create(
                buyer=account,
                status=OrderStatus.PAID,
                subtotal=0,
                shipping_fee=0,
                total=0,
                idempotency_key=payload.idempotency_key or None,
                payment_provenance=PaymentProvenance.FREE,
                **shipping_snapshot,
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                title=product.title,
                item_type=product.type,
                option=payload.option,
                qty=payload.qty,
                price=0,
            )
            record_free_grant(
                order=order, idempotency_key=payload.idempotency_key or None
            )
    except IntegrityError:
        if payload.idempotency_key:
            existing = _load_order_by_key(account, payload.idempotency_key)
            if existing is not None:
                return 200, _order_detail_out(existing)
        raise
    notify(
        account,
        NotificationKind.ORDER.value,
        f"'{product.title}' 무료 상품을 받았어요.",
        "/orders",
    )
    logger.info(
        "commerce.order.free_grant",
        extra={
            "order_id": order.id,
            "buyer_id": str(account.fan_id),
            "product_id": str(product.id),
            "qty": payload.qty,
        },
    )
    loaded = _load_order(order.id, account)
    assert loaded is not None  # just created for this buyer
    return 201, _order_detail_out(loaded)


@orders_router.get("", response=OrderPage)
def list_orders(
    request: HttpRequest, cursor: str | None = None, limit: int | None = None
) -> OrderPage:
    """List the requesting fan's own orders, newest first, cursor-paginated."""
    account = authed(request)
    queryset = (
        Order.objects.filter(buyer=account)
        .prefetch_related("items", "items__product", "items__product__creator", "refund_requests")
        .order_by("-created_at", "id")
    )
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return OrderPage(items=[_order_out(o) for o in items], next_cursor=next_cursor)


@orders_router.get("/{order_id}", response={200: OrderDetailOut, 404: CommerceError})
def get_order(
    request: HttpRequest, order_id: str
) -> tuple[int, OrderDetailOut | CommerceError]:
    """Return one of the requesting fan's own orders (404 if not theirs).

    The owner-scoped detail endpoint — the only place a fan's own delivery address
    (``shipping_address``) is exposed, one order at a time, never on the list (A-3).
    """
    account = authed(request)
    order = _load_order(order_id, account)
    if order is None:
        return 404, CommerceError(
            detail="주문을 찾을 수 없어요.", code=ErrorCode.ORDER_NOT_FOUND.value
        )
    return 200, _order_detail_out(order)


@orders_router.post(
    "/{order_id}/cancel",
    response={200: OrderDetailOut, 404: CommerceError, 422: CommerceError},
    throttle=user_write_throttle("6/min"),
)
def cancel_order(
    request: HttpRequest, order_id: str
) -> tuple[int, OrderDetailOut | CommerceError]:
    """Cancel one of the fan's own orders (only while paid/shipping).

    The cancellable → cancelled transition is sealed by a **conditional UPDATE
    rowcount gate** inside the transaction (project pattern): only the request whose
    ``filter(status__in=_CANCELLABLE).update(status=cancelled)`` touches a row (won
    the race) proceeds to restore stock; a concurrent second cancel updates 0 rows
    and returns 422 without restoring anything, so two racing cancels can never
    double-restore stock. The pre-check below is a friendly early return only — the
    rowcount gate is the actual invariant.

    Stock restore (winner only): each stock-tracked line's product is incremented by
    its ``qty`` (``F`` expression, no lost update). ``sold_out`` is only cleared for a
    product that had **hit 0** (auto sold-out) — a product an owner manually marked
    ``sold_out`` while stock remained keeps that flag (F-F): the restore adds stock
    but does not silently re-open a listing the owner paused. A since-deleted product
    line (SET_NULL) has nothing to restore and is skipped.

    A refund *accepted* (operator-approved) re-stock is a separate operator flow and
    is not handled here (후속 — 운영자 플로우).
    """
    account = authed(request)
    order = _load_order(order_id, account)
    if order is None:
        return 404, CommerceError(
            detail="주문을 찾을 수 없어요.", code=ErrorCode.ORDER_NOT_FOUND.value
        )
    if order.status not in _CANCELLABLE:
        return 422, CommerceError(
            detail="취소할 수 없는 주문 상태예요.", code=ErrorCode.ORDER_NOT_CANCELLABLE.value
        )
    with transaction.atomic():
        # Conditional transition: only the winner of the race flips the status and
        # gets to restore stock. 0 rows = a concurrent cancel already won → 422.
        transitioned = (
            Order.objects.filter(id=order.id, status__in=_CANCELLABLE)
            .update(status=OrderStatus.CANCELLED.value)
        )
        if transitioned == 0:
            return 422, CommerceError(
                detail="취소할 수 없는 주문 상태예요.",
                code=ErrorCode.ORDER_NOT_CANCELLABLE.value,
            )
        # Winner-only restock (the rowcount gate above proved this request won).
        _restock_order_lines(order)
        # Durably record the reversal of the original capture (#3 seam). Winner-only +
        # idempotent, so a losing/second cancel (0 rows above) never reaches here.
        _reverse_settled_order(order, reason="order_cancelled")
    # Reflect the committed transition on the in-memory instance for the response.
    order.status = OrderStatus.CANCELLED.value
    logger.info(
        "commerce.order.cancelled",
        extra={"order_id": order.id, "buyer_id": str(account.fan_id)},
    )
    return 200, _order_detail_out(order)


@orders_router.post(
    "/{order_id}/refund",
    response={200: OrderDetailOut, 404: CommerceError, 422: CommerceError},
    throttle=user_write_throttle("6/min"),
)
def request_refund(
    request: HttpRequest, order_id: str, payload: RefundIn
) -> tuple[int, OrderDetailOut | CommerceError]:
    """Request a refund against one of the fan's own orders (shipping/completed)."""
    account = authed(request)
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
            refund = RefundRequest.objects.create(
                order=order,
                reason=payload.reason,
                detail=payload.detail,
                status=RefundStatus.REQUESTED,
            )
    except IntegrityError:
        return 422, CommerceError(
            detail="이미 환불 신청이 접수된 주문이에요.", code=ErrorCode.OPEN_REFUND_EXISTS.value
        )
    logger.info(
        "commerce.refund.requested",
        extra={
            "order_id": order.id,
            "refund_id": str(refund.id),
            "buyer_id": str(account.fan_id),
        },
    )
    refreshed = _load_order(order_id, account)
    assert refreshed is not None  # owned above
    return 200, _order_detail_out(refreshed)


# --------------------------------------------------------------------------- #
# Fulfillment FSM (#11 — creator/operator drives PAID → SHIPPING → COMPLETED).
#
# MOCK/manual shipping: no real carrier integration — the product's creator-owner
# (or an operator) marks a PAID order SHIPPING with a carrier + tracking number,
# then COMPLETED. A digital-only order (no goods line) is "delivered" by completing
# it directly from PAID, skipping the shipping step (digital entitlement delivery).
#
# Authorization mirrors the studio owner guard + the operator RBAC ladder: only the
# creator that owns the order's product, or an operator+, may transition it. A
# non-owner (including the buyer) can't even load the order (leak-free 404), so a fan
# can never self-transition their own order. Each transition is sealed by the same
# conditional-UPDATE rowcount gate ``cancel_order`` uses: only the request whose
# ``filter(status=<from>).update(<to>)`` touches a row proceeds, so a concurrent
# double-ship / double-complete updates 0 rows and 422s without re-stamping.
# --------------------------------------------------------------------------- #
class ShipIn(Schema):
    """Creator/operator payload to ship a PAID order (carrier + tracking number)."""

    carrier: str = Field(min_length=1, max_length=60)
    tracking_number: str = Field(min_length=1, max_length=120)


def _load_fulfillable_order(order_id: str, account: Account) -> Order | None:
    """Load an order ``account`` may fulfill (prefetched), or ``None`` (→ 404, no leak).

    An operator+ may fulfill any order; anyone else may fulfill only an order whose
    product is owned by a creator they operate. A buyer or unrelated caller matches
    nothing → ``None`` (404), so order existence never leaks to a non-fulfiller and a
    fan can never self-transition their own order.
    """
    base = Order.objects.filter(id=order_id).prefetch_related(
        "items", "items__product", "items__product__creator", "refund_requests"
    )
    if has_min_role(account, minimum=Role.OPERATOR.value):
        return base.first()
    return base.filter(items__product__creator__owner=account).first()


@orders_router.post(
    "/{order_id}/ship",
    response={200: OrderDetailOut, 404: CommerceError, 422: CommerceError},
    throttle=user_write_throttle("30/min"),
)
def ship_order(
    request: HttpRequest, order_id: str, payload: ShipIn
) -> tuple[int, OrderDetailOut | CommerceError]:
    """Mark one of the caller's orders SHIPPING (creator-owner or operator; from PAID).

    Records the carrier + tracking number and stamps ``shipped_at``. The
    PAID→SHIPPING transition is sealed by the conditional-UPDATE rowcount gate
    (project pattern): shipping an order not in PAID (already shipping/completed/
    cancelled) updates 0 rows → 422 ``OrderNotShippable``. A digital order may skip
    this step and complete directly from PAID (see ``complete_order``).
    """
    account = authed(request)
    order = _load_fulfillable_order(order_id, account)
    if order is None:
        return 404, CommerceError(
            detail="주문을 찾을 수 없어요.", code=ErrorCode.ORDER_NOT_FOUND.value
        )
    carrier = payload.carrier.strip()
    number = payload.tracking_number.strip()
    now = timezone.now()
    with transaction.atomic():
        transitioned = Order.objects.filter(
            id=order.id, status=OrderStatus.PAID.value
        ).update(
            status=OrderStatus.SHIPPING.value,
            tracking_carrier=carrier,
            tracking_number=number,
            shipped_at=now,
        )
        if transitioned == 0:
            return 422, CommerceError(
                detail="배송 처리할 수 없는 주문 상태예요.",
                code=ErrorCode.ORDER_NOT_SHIPPABLE.value,
            )
    # Reflect the committed transition on the prefetched instance for the response.
    order.status = OrderStatus.SHIPPING.value
    order.tracking_carrier = carrier
    order.tracking_number = number
    order.shipped_at = now
    logger.info(
        "commerce.order.shipped",
        extra={"order_id": order.id, "actor_id": str(account.fan_id)},
    )
    return 200, _order_detail_out(order)


@orders_router.post(
    "/{order_id}/complete",
    response={200: OrderDetailOut, 404: CommerceError, 422: CommerceError},
    throttle=user_write_throttle("30/min"),
)
def complete_order(
    request: HttpRequest, order_id: str
) -> tuple[int, OrderDetailOut | CommerceError]:
    """Mark one of the caller's orders COMPLETED (creator-owner or operator).

    A physical (goods) order completes only from SHIPPING (it must ship first). A
    digital-only order (no goods line) completes directly from PAID — that is how a
    digital/coupon/ticket entitlement is "delivered" without a shipping step (#11 §3).
    The transition is sealed by the conditional-UPDATE rowcount gate: completing from
    any other state updates 0 rows → 422 ``OrderNotCompletable``.
    """
    account = authed(request)
    order = _load_fulfillable_order(order_id, account)
    if order is None:
        return 404, CommerceError(
            detail="주문을 찾을 수 없어요.", code=ErrorCode.ORDER_NOT_FOUND.value
        )
    # A goods line requires a prior shipping step; a digital-only order (no goods)
    # may be completed straight from PAID (digital delivery), so widen the allowed
    # from-states for it.
    has_goods = any(
        line.item_type == ProductType.GOODS.value for line in order.items.all()
    )
    from_states = [OrderStatus.SHIPPING.value]
    if not has_goods:
        from_states.append(OrderStatus.PAID.value)
    now = timezone.now()
    with transaction.atomic():
        transitioned = Order.objects.filter(
            id=order.id, status__in=from_states
        ).update(status=OrderStatus.COMPLETED.value, completed_at=now)
        if transitioned == 0:
            return 422, CommerceError(
                detail="완료 처리할 수 없는 주문 상태예요.",
                code=ErrorCode.ORDER_NOT_COMPLETABLE.value,
            )
    order.status = OrderStatus.COMPLETED.value
    order.completed_at = now
    logger.info(
        "commerce.order.completed",
        extra={"order_id": order.id, "actor_id": str(account.fan_id)},
    )
    return 200, _order_detail_out(order)


api.add_router("/orders", orders_router)


# --------------------------------------------------------------------------- #
# Studio order queue (#11 — the creator's own orders for fulfillment).
# Owner guard mirrors ``studio_list_products``: the caller must operate a creator,
# and the scope is always that creator's products (never taken from the request), so
# one creator can never see another's orders. Address-free rows (``OrderOut``) reuse
# the fan list schema — the delivery address is exposed only on the seller-scoped
# ship/complete responses (one order at a time), never enumerated across the list.
# --------------------------------------------------------------------------- #
studio_orders_router = Router(auth=fan_auth, tags=["studio-commerce"])


@studio_orders_router.get("", response={200: OrderPage, 403: CommerceError})
def studio_list_orders(
    request: HttpRequest, cursor: str | None = None, limit: int | None = None
) -> tuple[int, OrderPage | CommerceError]:
    """List orders for the caller's creator's products, newest first, cursor-paginated.

    Scoped to the caller's own creator (403 if they operate none) — an order is
    included when any of its lines is a product this creator owns, so another
    creator's orders never appear.
    """
    account = authed(request)
    creator = _owner_creator(account)
    if creator is None:
        return 403, CommerceError(
            detail="크리에이터만 주문을 관리할 수 있어요.", code=ErrorCode.OWNER_REQUIRED.value
        )
    queryset = (
        Order.objects.filter(items__product__creator=creator)
        .distinct()
        .prefetch_related(
            "items", "items__product", "items__product__creator", "refund_requests"
        )
        .order_by("-created_at", "id")
    )
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return 200, OrderPage(
        items=[_order_out(o) for o in items], next_cursor=next_cursor
    )


api.add_router("/studio/orders", studio_orders_router)


# --------------------------------------------------------------------------- #
# Operator refund review (R6-W1A — pure engineering; MOCK order flow, no money
# moves, B7-gated).
#
# The fan surface only *creates* a RefundRequest (request_refund above); this
# operator surface drives its review lifecycle. RBAC mirrors the safety operator
# pattern (apps/safety/api.py): the routes are gated by ``operator_required`` — a
# fan/anonymous caller is refused (401/403) by the auth class before the view runs.
# All four routes sit at operator+; refund processing is operator triage work and
# the flow is mock (no settlement), so a manager floor is unnecessary — if refund
# policy later needs a manager sign-off on accept, raise that one route's guard.
#
# Every transition is sealed by a **conditional-UPDATE rowcount gate** (the R5
# cancel lesson): ``filter(status__in=<from-states>).update(<to-state>)`` returning
# 0 rows means a concurrent operator already moved it → 422, so a double
# accept/reject can never re-run its side effects (restock, notify). Accept reuses
# the fan-cancel restock (``_restock_order_lines``) under its own order-side rowcount
# gate, so a refund accepted on an order a fan already cancelled never double-restores
# stock. Order status on accept moves to ``cancelled`` (an existing OrderStatus the
# web StatusChip already renders) rather than a new ``refunded`` value: the web lane
# is evolving in parallel and a status it does not yet handle would break the chip,
# and the embedded ``refund.status = accepted`` on the order already conveys
# "refunded" to the fan surface — so cancelled + accepted-refund is the
# backward-compatible encoding. The fan surface is otherwise unchanged.
# --------------------------------------------------------------------------- #
ops_refunds_router = Router(auth=operator_required, tags=["ops-commerce"])


class OpsRefundOut(Schema):
    """A refund request as seen in the operator review queue.

    Carries the request fields plus the minimal owning-order context an operator
    tool needs to triage (buyer's public fan id, current order status, order total
    — a display snapshot, never a settlement figure).
    """

    id: uuid.UUID
    order_id: str
    status: str
    reason: str
    detail: str
    created_at: datetime
    buyer_fan_id: uuid.UUID
    order_status: str
    order_total: int


class OpsRefundPage(Schema):
    """One page of the operator refund queue plus the next cursor."""

    items: list[OpsRefundOut]
    next_cursor: str | None = None


class OpsRefundRejectIn(Schema):
    """Operator payload to reject a refund; a reason is mandatory (audited)."""

    reason: str = Field(min_length=1, max_length=200)


def _ops_actor(request: HttpRequest) -> Account:
    """Return the operator account supplied by ``operator_required`` (RBAC guard)."""
    # request.auth is the Account resolved by RoleRequired; untyped without Ninja
    # stubs (same idiom as apps/safety/api.py._actor).
    return authed(request)


def _ops_refund_out(refund: RefundRequest) -> OpsRefundOut:
    """Build the operator refund-queue row from a refund with its order prefetched."""
    order = refund.order
    return OpsRefundOut(
        id=refund.id,
        order_id=order.id,
        status=refund.status,
        reason=refund.reason,
        detail=refund.detail,
        created_at=refund.created_at,
        buyer_fan_id=order.buyer.fan_id,
        order_status=order.status,
        order_total=order.total,
    )


def _load_refund(refund_id: uuid.UUID) -> RefundRequest | None:
    """Load a refund with its order/buyer/lines prefetched, or ``None`` (→ 404)."""
    return (
        RefundRequest.objects.select_related("order", "order__buyer")
        .prefetch_related("order__items", "order__items__product")
        .filter(id=refund_id)
        .first()
    )


@ops_refunds_router.get("", response=OpsRefundPage)
def ops_list_refunds(
    request: HttpRequest, cursor: str | None = None, limit: int | None = None
) -> OpsRefundPage:
    """List open refund requests (requested/reviewing), newest first, cursor-paginated.

    Not caller-scoped: the whole platform's pending refund queue is an operator
    surface (the ``operator_required`` guard is the access control).
    """
    del request  # operator auth only; the queue is global, not caller-scoped.
    queryset = (
        RefundRequest.objects.filter(status__in=_OPEN_REFUND)
        .select_related("order", "order__buyer")
        .order_by("-created_at", "id")
    )
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return OpsRefundPage(
        items=[_ops_refund_out(r) for r in items], next_cursor=next_cursor
    )


@ops_refunds_router.post(
    "/{refund_id}/review",
    response={200: OpsRefundOut, 404: CommerceError, 422: CommerceError},
)
def ops_review_refund(
    request: HttpRequest, refund_id: uuid.UUID
) -> tuple[int, OpsRefundOut | CommerceError]:
    """Move a refund requested→reviewing (operator+). 422 if not in ``requested``."""
    refund = _load_refund(refund_id)
    if refund is None:
        return 404, CommerceError(
            detail="환불 신청을 찾을 수 없어요.", code=ErrorCode.REFUND_NOT_FOUND.value
        )
    # Transition + audit are one atomic unit (symmetric with accept/reject): if the
    # audit write fails, the requested→reviewing transition rolls back rather than
    # leaving a state change with no audit trail.
    with transaction.atomic():
        transitioned = RefundRequest.objects.filter(
            id=refund.id, status=RefundStatus.REQUESTED.value
        ).update(status=RefundStatus.REVIEWING.value)
        if transitioned == 0:
            return 422, CommerceError(
                detail="검토로 전환할 수 없는 상태예요.",
                code=ErrorCode.REFUND_NOT_TRANSITIONABLE.value,
            )
        record_audit(
            actor=_ops_actor(request),
            action=AuditAction.REFUND_REVIEWED.value,
            target=str(refund.id),
        )
    refund.status = RefundStatus.REVIEWING.value
    return 200, _ops_refund_out(refund)


@ops_refunds_router.post(
    "/{refund_id}/accept",
    response={200: OpsRefundOut, 404: CommerceError, 422: CommerceError},
)
def ops_accept_refund(
    request: HttpRequest, refund_id: uuid.UUID
) -> tuple[int, OpsRefundOut | CommerceError]:
    """Accept a refund (operator+): resolve it, cancel + restock the order, notify the fan.

    The refund requested/reviewing→accepted transition is the rowcount gate: 0 rows
    means a concurrent accept/reject already resolved it → 422 (so a double accept
    cannot re-run the restock). The order is cancelled + restocked only when it is
    still in a refundable (active) state — a second, independent rowcount gate — so a
    refund accepted on an order a fan already cancelled does not double-restore stock
    (the fan cancel restocked it then). Money never moves (mock, B7). The fan
    notification is sent after commit so a rolled-back accept emits nothing.
    """
    refund = _load_refund(refund_id)
    if refund is None:
        return 404, CommerceError(
            detail="환불 신청을 찾을 수 없어요.", code=ErrorCode.REFUND_NOT_FOUND.value
        )
    order = refund.order
    with transaction.atomic():
        transitioned = RefundRequest.objects.filter(
            id=refund.id, status__in=_OPEN_REFUND
        ).update(status=RefundStatus.ACCEPTED.value)
        if transitioned == 0:
            return 422, CommerceError(
                detail="승인할 수 없는 환불 상태예요.",
                code=ErrorCode.REFUND_NOT_TRANSITIONABLE.value,
            )
        # Cancel + restock the order only if it is still active (refundable). If a
        # fan already cancelled it meanwhile, it was restocked then → 0 rows, skip.
        order_cancelled = (
            Order.objects.filter(id=order.id, status__in=_REFUNDABLE)
            .update(status=OrderStatus.CANCELLED.value)
        )
        if order_cancelled:
            _restock_order_lines(order)
            # Reverse the original capture only when THIS accept won the order-cancel
            # (a fan cancel that raced in first already recorded it) — mirrors the
            # winner-only restock, so the reversal is never double-recorded (#3 seam).
            _reverse_settled_order(order, reason="refund_accepted")
            order.status = OrderStatus.CANCELLED.value
        else:
            # The order already left the refundable window (e.g. a fan cancel raced in
            # first), so reload its committed status — the value read at load time may
            # be stale, and the response echoes ``order_status``.
            order.refresh_from_db(fields=["status"])
        record_audit(
            actor=_ops_actor(request),
            action=AuditAction.REFUND_ACCEPTED.value,
            target=str(refund.id),
        )
    refund.status = RefundStatus.ACCEPTED.value
    notify(
        order.buyer,
        NotificationKind.ORDER.value,
        f"주문 {order.id}의 환불이 승인되었어요.",
        "/orders",
    )
    logger.info(
        "commerce.refund.accepted",
        extra={
            "refund_id": str(refund.id),
            "order_id": order.id,
            "actor_id": str(_ops_actor(request).fan_id),
            "order_restocked": bool(order_cancelled),
        },
    )
    return 200, _ops_refund_out(refund)


@ops_refunds_router.post(
    "/{refund_id}/reject",
    response={200: OpsRefundOut, 404: CommerceError, 422: CommerceError},
)
def ops_reject_refund(
    request: HttpRequest, refund_id: uuid.UUID, payload: OpsRefundRejectIn
) -> tuple[int, OpsRefundOut | CommerceError]:
    """Reject a refund requested/reviewing→rejected (operator+); reason mandatory.

    The reason is required (schema) and recorded on the audit entry so a refusal
    always answers "why". The rowcount gate makes it single-winner (a concurrent
    accept/reject leaves the loser with 0 rows → 422). The order is left untouched
    (only accept cancels/restocks). The fan is notified of the outcome after commit.
    """
    refund = _load_refund(refund_id)
    if refund is None:
        return 404, CommerceError(
            detail="환불 신청을 찾을 수 없어요.", code=ErrorCode.REFUND_NOT_FOUND.value
        )
    with transaction.atomic():
        transitioned = RefundRequest.objects.filter(
            id=refund.id, status__in=_OPEN_REFUND
        ).update(status=RefundStatus.REJECTED.value)
        if transitioned == 0:
            return 422, CommerceError(
                detail="거절할 수 없는 환불 상태예요.",
                code=ErrorCode.REFUND_NOT_TRANSITIONABLE.value,
            )
        record_audit(
            actor=_ops_actor(request),
            action=AuditAction.REFUND_REJECTED.value,
            target=str(refund.id),
            reason=payload.reason,
        )
    refund.status = RefundStatus.REJECTED.value
    notify(
        refund.order.buyer,
        NotificationKind.ORDER.value,
        f"주문 {refund.order.id}의 환불이 거절되었어요.",
        "/orders",
    )
    logger.warning(
        "commerce.refund.rejected",
        extra={
            "refund_id": str(refund.id),
            "order_id": refund.order.id,
            "actor_id": str(_ops_actor(request).fan_id),
        },
    )
    return 200, _ops_refund_out(refund)


api.add_router("/ops/refunds", ops_refunds_router)
