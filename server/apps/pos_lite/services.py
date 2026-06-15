"""Service layer for manual POS ↔ Platform order linking (ASS-102 v0).

Every POS-link mutation passes through this module so the operational row, the
audit trail, and the append-only analytics event stay coupled. Analytics events
are emitted **only** through :func:`apps.event_log.services.emit_event` (the
validated registry) — mirrors the visit/cheki domains.

Event mapping (Data_Event_Schema):

- link            → ``pos_order_linked``  (visit ↔ POS receipt/order)
- link w/ refund  → also ``payment_refunded`` (the canonical MSFC-exclusion
  signal; refunded/cancelled payments are kept as a *separate status* here and on
  the link event, satisfying "환불/취소는 ... 제외 또는 별도 상태")
- void            → **audit only**; ``pos_order_unlinked`` is not in the code
  registry yet, so an unlink is an operational fact recorded in the audit log and
  by flipping ``reconciliation_status=excluded``.

Out of scope for v0 (held): CSV import + daily reconciliation (POS vendor
selection, OQ-C) and wiring ``payment_status=refunded`` into the MSFC *query*
(a focused follow-up across event_log/dashboard/membership-card).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import emit_event
from apps.identity.models import Account
from apps.pos_lite.models import (
    LinkedConfidence,
    LinkMethod,
    PaymentMethod,
    PaymentStatus,
    PosOrder,
    PosOrderStatus,
    ReconciliationStatus,
    RefundReason,
)
from apps.visit.models import VisitRecord, VisitRecordStatus


@transaction.atomic
def link_pos_order(
    *,
    visit: VisitRecord,
    actor: Account,
    pos_receipt_no: str = "",
    pos_order_id: str = "",
    payment_status: str = PaymentStatus.UNKNOWN.value,
    payment_method: str = PaymentMethod.UNKNOWN.value,
    amount: Decimal | None = None,
    pos_vendor_name: str = "",
    linked_confidence: str = LinkedConfidence.MANUAL.value,
    refund_reason: str = "",
    business_day: date | None = None,
) -> PosOrder:
    """Manually link a POS order/receipt to a visit and emit its side effects.

    Rejects linking against a voided visit (the visit never happened, so a POS
    link would leak into reconciliation), a link carrying neither a receipt nor an
    order number, and a duplicate active receipt number (also DB-enforced). A
    ``payment_status=refunded`` link additionally emits the canonical
    ``payment_refunded`` event so the refund is a first-class exclusion signal.
    """
    if visit.status == VisitRecordStatus.VOIDED.value:
        raise ValueError("Cannot link a POS order to a voided visit.")
    receipt = pos_receipt_no.strip()
    order_no = pos_order_id.strip()
    if not receipt and not order_no:
        raise ValueError("A POS link needs at least a receipt number or an order number.")
    _validate_enum(payment_status, PaymentStatus, "payment_status")
    _validate_enum(payment_method, PaymentMethod, "payment_method")
    _validate_enum(linked_confidence, LinkedConfidence, "linked_confidence")
    if amount is not None and amount < 0:
        raise ValueError("amount must not be negative.")
    # A refunded *or* cancelled payment is a first-class exclusion fact; coerce its
    # reason to the coded domain (default ``other``) up front so an invalid value
    # is rejected before any write (the whole body is atomic anyway).
    is_refund = payment_status in (PaymentStatus.REFUNDED.value, PaymentStatus.CANCELLED.value)
    refund_reason_value = ""
    if is_refund:
        refund_reason_value = refund_reason.strip() or RefundReason.OTHER.value
        _validate_enum(refund_reason_value, RefundReason, "refund_reason")
    if (
        receipt
        and PosOrder.objects.filter(
            pos_receipt_no=receipt,
            status=PosOrderStatus.ACTIVE.value,
        ).exists()
    ):
        # Friendly error ahead of the DB unique constraint, which is the
        # race-safe backstop.
        raise ValueError(f"Receipt '{receipt}' is already linked to an active POS order.")

    day = business_day or timezone.localdate(visit.visited_at)
    record = PosOrder.objects.create(
        visit=visit,
        pos_receipt_no=receipt,
        pos_order_id=order_no,
        business_day=day,
        payment_status=payment_status,
        payment_method=payment_method,
        amount=amount,
        link_method=LinkMethod.MANUAL.value,
        linked_confidence=linked_confidence,
        pos_vendor_name=pos_vendor_name.strip(),
        created_by=actor,
    )
    record_audit(
        actor=actor,
        action=AuditAction.POS_ORDER_LINKED.value,
        target=str(record.id),
        metadata={
            "visit_id": str(visit.id),
            "pos_receipt_no": receipt,
            "pos_order_id": order_no,
            "payment_status": payment_status,
        },
    )

    ids: dict[str, str] = {"visit_id": str(visit.id)}
    if order_no:
        ids["pos_order_id"] = order_no
    if receipt:
        ids["pos_receipt_no"] = receipt
    payload: dict[str, object] = {
        "visit_id": str(visit.id),
        "link_method": LinkMethod.MANUAL.value,
        "payment_status": payment_status,
        "linked_confidence": linked_confidence,
    }
    if amount is not None:
        # Serialise the money figure as a string so the JSON ledger keeps the
        # exact decimal (no float rounding).
        payload["payment_amount"] = str(amount)
    if payment_method != PaymentMethod.UNKNOWN.value:
        payload["payment_method"] = payment_method
    if record.pos_vendor_name:
        payload["pos_vendor_name"] = record.pos_vendor_name
    emit_event(
        event_name=EventName.POS_ORDER_LINKED.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_id=str(actor.fan_id),
        visit_id=str(visit.id),
        # pos_order_linked is not itself an MSFC input (Data_Event_Schema: "이
        # 이벤트 자체는 MSFC에 포함하지 않는다"), so this flag carries no metric
        # weight; kept False for consistency with the sibling domains.
        actor_is_operator=False,
        ids=ids,
        context={"store_id": visit.store_id, "business_day": day.isoformat()},
        payload=payload,
        quality={"created_by_operator_id": str(actor.fan_id)},
    )

    if is_refund:
        refund_type = "cancellation" if payment_status == PaymentStatus.CANCELLED.value else "full"
        _emit_payment_refunded(
            visit=visit,
            actor=actor,
            refund_type=refund_type,
            refund_reason=refund_reason_value,
            receipt=receipt,
            order_no=order_no,
        )
    return record


@transaction.atomic
def void_pos_order(*, order: PosOrder, reason: str, actor: Account) -> PosOrder:
    """Void a POS link (never delete) so the receipt frees up and it is excluded.

    The row flips to ``voided`` with ``reconciliation_status=excluded`` so it
    never enters a future daily reconciliation; the audit log carries the trail.
    Re-voiding is rejected. No analytics event is emitted: ``pos_order_unlinked``
    is not in the code registry yet (P0_conditional, lands with reconciliation).
    """
    if order.status == PosOrderStatus.VOIDED.value:
        raise ValueError("POS order is already voided.")
    if not reason.strip():
        raise ValueError("Void reason is required.")

    order.status = PosOrderStatus.VOIDED.value
    order.void_reason = reason.strip()
    order.reconciliation_status = ReconciliationStatus.EXCLUDED.value
    order.save(update_fields=["status", "void_reason", "reconciliation_status", "updated_at"])
    record_audit(
        actor=actor,
        action=AuditAction.POS_ORDER_VOIDED.value,
        target=str(order.id),
        reason=order.void_reason,
        metadata={"visit_id": str(order.visit_id), "pos_receipt_no": order.pos_receipt_no},
    )
    return order


def _emit_payment_refunded(
    *,
    visit: VisitRecord,
    actor: Account,
    refund_type: str,
    refund_reason: str,
    receipt: str,
    order_no: str,
) -> None:
    """Emit the canonical ``payment_refunded`` exclusion signal for a visit.

    Covers both refunds (``refund_type=full``; partial refunds arrive with the
    held CSV reconciliation) and cancellations (``cancellation``). The receipt/
    order ids travel so the deferred MSFC wiring can net the refund against the
    specific POS order, not just the visit (Data_Event_Schema payment_refunded
    ids.pos_receipt_no/ids.pos_order_id). ``refund_reason`` is a coded value.
    """
    ids: dict[str, str] = {"visit_id": str(visit.id)}
    if receipt:
        ids["pos_receipt_no"] = receipt
    if order_no:
        ids["pos_order_id"] = order_no
    emit_event(
        event_name=EventName.PAYMENT_REFUNDED.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_id=str(actor.fan_id),
        visit_id=str(visit.id),
        actor_is_operator=False,
        ids=ids,
        context={"store_id": visit.store_id},
        payload={"refund_type": refund_type, "refund_reason": refund_reason},
    )


def _validate_enum(value: str, choices: type[models.TextChoices], field: str) -> None:
    """Raise ``ValueError`` if ``value`` is not a member of ``choices``."""
    if value not in choices.values:
        raise ValueError(f"Unknown {field} '{value}'.")
