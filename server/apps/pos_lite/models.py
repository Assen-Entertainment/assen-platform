"""Domain models for pos_lite — the POS ↔ Platform reconciliation ledger.

POS Lite (ASS-102, F13) links the *external* POS payment ledger to the
Platform's visit/fandom ledger. Per ``P0_Scope_Reconciliation`` G-2/OQ-C the P0
work is split: **manual receipt/order linking is POS-vendor-independent (R0.2)
and is what this app implements**; CSV import + daily reconciliation is held
until a POS vendor is selected (OQ-C, an operational gate).

This is a deliberately independent ``pos_*`` intermediate ledger
(``POS_Integration_Plan`` §리스크: "POS 변경 → 데이터 이전 비용 → POS 독립 pos_*
중간 모델 유지"), so swapping POS vendors never pollutes the platform's fan/visit
ledger.

Money: ``amount`` is the **POS-reported figure** — an imported external fact for
reconciliation. Assen Platform is not the payment ledger and does not decide
settlement; ``POS_Integration_Plan`` §개인정보/결제정보 explicitly lists 결제 금액
as storable, while the sensitive card data it forbids (PAN/CVC/등) is never
modelled here. The cheki domain's "never a money figure" rule is about
*settlement* decisions, which this app likewise never makes — it only records
what POS already charged so the daily reconciliation (held) can compare totals.
"""

from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q


class PaymentStatus(models.TextChoices):
    """Payment outcome of a POS order (Data_Event_Schema payment_status domain)."""

    PAID = "paid", "paid"
    REFUNDED = "refunded", "refunded"
    CANCELLED = "cancelled", "cancelled"
    UNPAID = "unpaid", "unpaid"
    # POS not yet linked / amount unconfirmed starts here (Data_Event_Schema
    # L734-741: "POS 없음 → payment_status = unknown").
    UNKNOWN = "unknown", "unknown"


class PaymentMethod(models.TextChoices):
    """Payment instrument class — never the raw card number (privacy §)."""

    CASH = "cash", "cash"
    CARD = "card", "card"
    TRANSFER = "transfer", "transfer"
    SIMPLE_PAY = "simple_pay", "simple_pay"
    MIXED = "mixed", "mixed"
    UNKNOWN = "unknown", "unknown"


class RefundReason(models.TextChoices):
    """Why a payment was refunded/cancelled (Data_Event_Schema refund_reason).

    A coded value (not free text) so the canonical ``payment_refunded`` ledger
    stays queryable; defaults to ``other`` when an operator gives none.
    """

    CUSTOMER_REQUEST = "customer_request", "customer_request"
    MISTAKE = "mistake", "mistake"
    SAFETY_DISPUTE = "safety_dispute", "safety_dispute"
    TEST = "test", "test"
    OTHER = "other", "other"


class LinkMethod(models.TextChoices):
    """How the POS order was linked to the visit (Data_Event_Schema link_method).

    Only ``manual`` is reachable in P0; the match variants are forward-compat for
    the held CSV/API reconciliation (OQ-C).
    """

    MANUAL = "manual", "manual"
    CSV_MATCH = "csv_match", "csv_match"
    API_MATCH = "api_match", "api_match"
    WEBHOOK_MATCH = "webhook_match", "webhook_match"


class LinkedConfidence(models.TextChoices):
    """Confidence of the link (Data_Event_Schema linked_confidence domain)."""

    EXACT = "exact", "exact"
    LIKELY = "likely", "likely"
    MANUAL = "manual", "manual"
    UNKNOWN = "unknown", "unknown"


class ReconciliationStatus(models.TextChoices):
    """Reconciliation state of the order (POS_Integration_Plan pos_order model).

    P0 manual links start ``unmatched`` (no daily reconciliation runs yet, OQ-C);
    a void marks the row ``excluded`` so it never enters a future reconciliation.
    """

    MATCHED = "matched", "matched"
    UNMATCHED = "unmatched", "unmatched"
    DISPUTED = "disputed", "disputed"
    EXCLUDED = "excluded", "excluded"


class PosOrderStatus(models.TextChoices):
    """Lifecycle for a POS link that is never physically deleted."""

    ACTIVE = "active", "active"
    VOIDED = "voided", "voided"


class PosOrder(models.Model):
    """A manually-entered link between a POS order/receipt and a Platform visit.

    Append-oriented like the visit/cheki rows: a wrong link is *voided* (not
    deleted) so the reconciliation trail survives. Exactly one POS order may hold
    a given non-empty receipt number while active (the partial unique constraint),
    which is the DB-enforced "영수증 번호 중복 감지" — voiding frees it for re-link.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(
        "visit.VisitRecord",
        on_delete=models.PROTECT,
        related_name="pos_orders",
    )
    # At least one of receipt/order number is required (enforced in the service);
    # ``pos_receipt_no`` is "P0 수동 연결의 핵심" (Data_Event_Schema L532).
    pos_receipt_no = models.CharField(max_length=64, blank=True, default="")
    pos_order_id = models.CharField(max_length=64, blank=True, default="")
    business_day = models.DateField()
    payment_status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNKNOWN,
    )
    payment_method = models.CharField(
        max_length=16,
        choices=PaymentMethod.choices,
        default=PaymentMethod.UNKNOWN,
    )
    # The POS-reported total (imported external fact); null when unconfirmed
    # (Data_Event_Schema L741: "결제 금액 미확인 → payment_amount = null").
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    link_method = models.CharField(
        max_length=16,
        choices=LinkMethod.choices,
        default=LinkMethod.MANUAL,
    )
    linked_confidence = models.CharField(
        max_length=16,
        choices=LinkedConfidence.choices,
        default=LinkedConfidence.MANUAL,
    )
    # Vendor name travels as data (not a model/FK) so a POS change is a string
    # edit, not a migration (Data_Event_Schema L736: properties.pos_vendor_name).
    pos_vendor_name = models.CharField(max_length=64, blank=True, default="")
    reconciliation_status = models.CharField(
        max_length=16,
        choices=ReconciliationStatus.choices,
        default=ReconciliationStatus.UNMATCHED,
    )
    status = models.CharField(
        max_length=16,
        choices=PosOrderStatus.choices,
        default=PosOrderStatus.ACTIVE,
    )
    void_reason = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_pos_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # One active link per non-empty receipt number — the DB-enforced
            # duplicate guard (a void drops out of ``active`` so re-link works).
            models.UniqueConstraint(
                fields=["pos_receipt_no"],
                condition=Q(status="active") & ~Q(pos_receipt_no=""),
                name="uniq_active_pos_receipt_no",
            ),
        ]
        indexes = [
            models.Index(fields=["business_day"]),
            models.Index(fields=["visit"]),
            models.Index(fields=["status", "business_day"]),
            models.Index(fields=["reconciliation_status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the POS link by receipt/order and visit for admin display."""
        ref = self.pos_receipt_no or self.pos_order_id or "?"
        return f"pos_order:{self.id}:{ref}->visit:{self.visit_id}"
