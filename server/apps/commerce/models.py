"""Commerce models — Product catalog + mock Order flow (SDLC 09 §3, E11/B1·B4).

The *catalog* (``Product``) is a display listing with a catalog ``price``
(integer KRW, a display value — NOT a settlement figure). B4 adds a **mock**
order flow (``Order``/``OrderItem``/``RefundRequest``): placing an order records
a paid order and snapshots the line items, but **no real payment is taken and no
money moves** — real PG, amounts, and settlement are gated (B7, 대표·법무·PG).
Every stored monetary value is a display snapshot, never a settlement figure.

Migrated app — ``migrate`` applies ``0001_initial``; regenerate with
``makemigrations`` when models change.
"""

from __future__ import annotations

import uuid

from django.db import models

from config.payment import PaymentProvenance, PricingKind


class ProductType(models.TextChoices):
    """Monetizable item kinds (mirror the frontend ``MonetizableItemType``)."""

    GOODS = "goods", "goods"
    DIGITAL = "digital", "digital"
    EXPERIENCE = "experience", "experience"
    TICKET = "ticket", "ticket"
    COUPON = "coupon", "coupon"


class ProductStatus(models.TextChoices):
    """Studio-managed catalog lifecycle state (owner view; R3).

    ``selling`` / ``soldout`` are public; ``draft`` / ``hidden`` are owner-only and
    excluded from the consumer ``list_products``. Distinct from the ``sold_out``
    order-flow boolean (which blocks ordering) — ``status`` drives *visibility*.
    """

    SELLING = "selling", "selling"
    SOLDOUT = "soldout", "soldout"
    DRAFT = "draft", "draft"
    HIDDEN = "hidden", "hidden"


class Product(models.Model):
    """A catalog listing (maps to the frontend ``Product`` type)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
        "creator.Creator",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="products",
    )
    type = models.CharField(max_length=16, choices=ProductType.choices)
    title = models.CharField(max_length=120)
    # Catalog display price in whole KRW (integer currency). Not a settlement.
    price = models.PositiveIntegerField(default=0)
    # Explicit price intent (ASS-297): PAID by default, so a price-0 row is a
    # placeholder, not free. Only a FREE offering may be acquired via /orders/free.
    pricing_kind = models.CharField(
        max_length=8, choices=PricingKind.choices, default=PricingKind.PAID
    )
    meta = models.CharField(max_length=120, blank=True, default="")
    media_url = models.CharField(max_length=500, blank=True, default="")
    # Long-form description shown on the product detail page.
    description = models.TextField(blank=True, default="")
    # Nullable stock: None = untracked/unlimited; an int caps availability. 0 (or
    # sold_out) means the listing cannot be ordered.
    stock = models.PositiveIntegerField(null=True, blank=True)
    sold_out = models.BooleanField(default=False)
    # Locked = membership/subscription-gated listing (LockedOverlay on the web).
    locked = models.BooleanField(default=False)
    # Studio visibility lifecycle (R3): public list shows selling/soldout only;
    # draft/hidden are owner-only. Separate from the ``sold_out`` order-flow flag.
    status = models.CharField(
        max_length=16, choices=ProductStatus.choices, default=ProductStatus.SELLING
    )
    # 19+ 성인 등급. 공개 read는 ENABLE_ADULT_CONTENT + adult_verified 뷰어에게만
    # 노출(플래그 off면 전원 숨김 — R3 정본 §55). 저장은 등급 플래그뿐.
    adult_only = models.BooleanField(default=False)
    # Selectable option labels (frontend ``options: string[]``), e.g. ["A타입"].
    options = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["creator", "-created_at"]),
            models.Index(fields=["type"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the product."""
        return f"{self.type}:{self.title}"


class OrderStatus(models.TextChoices):
    """Order lifecycle states surfaced to the fan (StatusChip on the web).

    The 2-phase payment intent (#4/#2) adds two internal states: ``PENDING`` — the
    order is durably persisted and its stock reserved, but the gateway capture has
    not been verified yet — and ``FAILED`` — the capture declined, so the order is
    dead and its reserved stock was restored. A mock checkout passes through PENDING
    synchronously and ends PAID; PENDING/FAILED become fan-visible only when a real
    async PG is wired. ``PAID`` and later states are unchanged (fulfillment #11
    still starts from PAID).
    """

    PENDING = "pending", "pending"
    PAID = "paid", "paid"
    SHIPPING = "shipping", "shipping"
    COMPLETED = "completed", "completed"
    CANCELLED = "cancelled", "cancelled"
    FAILED = "failed", "failed"


class RefundStatus(models.TextChoices):
    """Refund-request review states (operator-driven; mock in B4)."""

    REQUESTED = "requested", "requested"
    REVIEWING = "reviewing", "reviewing"
    ACCEPTED = "accepted", "accepted"
    REJECTED = "rejected", "rejected"


def _order_code() -> str:
    """Generate a human-readable order code (e.g. ``ASN-1A2B3C4D5E6F``).

    Used as the ``Order`` primary key so it is safe to show to fans and put in
    URLs. Uniqueness is enforced by the PK; collisions are astronomically
    unlikely for the 12 hex chars (B1 — widened from 8 to shrink the birthday-
    collision window) and would surface as an insert error.
    """
    return f"ASN-{uuid.uuid4().hex[:12].upper()}"


class Order(models.Model):
    """A fan's mock order. MOCK: no real payment is taken and no money moves.

    ``subtotal``/``shipping_fee``/``total`` are display snapshots computed at
    purchase (``total = subtotal + shipping_fee``) — real PG, amounts, and
    settlement are gated (B7), so nothing here decides money owed. The
    ``recipient_*``/``postal_code``/``address*`` fields snapshot the delivery
    address for a physical (``goods``) order; the fan sees only their own orders,
    so echoing them back is safe. Real operation must reflect the delivery-address
    items in the privacy policy (법무 확인); the mock contract flow is un-gated.
    """

    id = models.CharField(
        primary_key=True, max_length=20, default=_order_code, editable=False
    )
    buyer = models.ForeignKey(
        "identity.Account", on_delete=models.CASCADE, related_name="orders"
    )
    status = models.CharField(
        max_length=16, choices=OrderStatus.choices, default=OrderStatus.PAID
    )
    # Display snapshots of the order amounts (KRW). NOT settlement figures.
    # ``subtotal`` is the sum of line ``price`` × ``qty``; ``shipping_fee`` is the
    # server-authoritative delivery charge (fixed at 0 until the fee policy is set —
    # 대표·재무 게이트); ``total`` = subtotal + shipping_fee.
    subtotal = models.PositiveIntegerField(default=0)
    shipping_fee = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    # Delivery-address snapshot for physical (goods) orders; blank for
    # digital/experience/ticket/coupon orders that need no shipping.
    recipient_name = models.CharField(max_length=60, blank=True, default="")
    recipient_phone = models.CharField(max_length=32, blank=True, default="")
    postal_code = models.CharField(max_length=16, blank=True, default="")
    address1 = models.CharField(max_length=200, blank=True, default="")
    address2 = models.CharField(max_length=200, blank=True, default="")
    # Optional client-supplied idempotency key (B1). When set, a retried POST with
    # the same (buyer, key) returns the existing order instead of duplicating it;
    # the partial unique constraint below makes that race-safe. NULL = not supplied.
    idempotency_key = models.CharField(max_length=64, null=True, blank=True, default=None)
    # How this order's PAID state was settled (ASS-298). Set explicitly on every
    # write (mock/free); the LEGACY_UNKNOWN default only ever applies to rows that
    # predate this column — never a guessed value.
    payment_provenance = models.CharField(
        max_length=16,
        choices=PaymentProvenance.choices,
        default=PaymentProvenance.LEGACY_UNKNOWN,
    )
    # Fulfillment snapshot (mock/manual shipping — no real carrier integration; the
    # creator/operator marks the order SHIPPING with a carrier + tracking number and
    # then COMPLETED). ``tracking_*`` are blank until a physical order ships; a
    # digital order is completed directly from PAID and carries no tracking. The
    # timestamps stamp when each transition happened (NULL until it does).
    tracking_carrier = models.CharField(max_length=60, blank=True, default="")
    tracking_number = models.CharField(max_length=120, blank=True, default="")
    shipped_at = models.DateTimeField(null=True, blank=True, default=None)
    completed_at = models.DateTimeField(null=True, blank=True, default=None)
    # Payment-intent snapshot (#4/#2 2-phase checkout). An order is persisted PENDING
    # (stock reserved) and only transitions to PAID after the gateway capture is
    # verified — or to FAILED (stock restored) on a decline. ``paid_at``/``failed_at``
    # stamp when each terminal transition happened (NULL until it does); ``payment_ref``
    # records the gateway's own transaction reference on a verified capture (the mock
    # id today, a real PG's imp_uid/tid when wired) — never a card PAN.
    paid_at = models.DateTimeField(null=True, blank=True, default=None)
    failed_at = models.DateTimeField(null=True, blank=True, default=None)
    payment_ref = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["buyer", "-created_at"]),
            models.Index(fields=["payment_provenance"]),
        ]
        ordering = ["-created_at"]
        constraints = [
            # One order per (buyer, idempotency_key), but only when a key is
            # supplied — keyless orders (key IS NULL) are never deduped.
            # Materialised by the app's migration (applied by ``migrate``).
            models.UniqueConstraint(
                fields=["buyer", "idempotency_key"],
                condition=models.Q(idempotency_key__isnull=False),
                name="uniq_order_buyer_idempotency_key",
            ),
        ]

    def __str__(self) -> str:
        """Identify the order by its human-readable code."""
        return f"order:{self.id}"


class OrderItem(models.Model):
    """One line of an order, snapshotting the product at purchase time.

    ``product`` is nullable (``SET_NULL``) so deleting a catalog product keeps the
    historical order line intact; ``title``/``item_type``/``price`` are snapshots
    so the line renders stably even if the catalog later changes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "commerce.Product",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )
    title = models.CharField(max_length=120)
    item_type = models.CharField(max_length=16, choices=ProductType.choices)
    option = models.CharField(max_length=120, blank=True, default="")
    qty = models.PositiveIntegerField(default=1)
    # Snapshot of the unit price at purchase (KRW). NOT a settlement figure.
    price = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        """Identify the order line."""
        return f"order_item:{self.id}"


class RefundRequest(models.Model):
    """A fan's refund request against an order (mock review workflow, B4)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="refund_requests"
    )
    reason = models.CharField(max_length=120)
    detail = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16, choices=RefundStatus.choices, default=RefundStatus.REQUESTED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["order", "-created_at"]),
        ]
        ordering = ["-created_at"]
        constraints = [
            # 열린 환불(requested/reviewing)은 주문당 1건 — check-then-create 경합을
            # DB 불변식으로 봉인(동시 신청 시 IntegrityError → API가 422로 변환).
            models.UniqueConstraint(
                fields=["order"],
                condition=models.Q(status__in=("requested", "reviewing")),
                name="uniq_open_refund_per_order",
            ),
        ]

    def __str__(self) -> str:
        """Identify the refund request and its state."""
        return f"refund:{self.id}:{self.status}"
