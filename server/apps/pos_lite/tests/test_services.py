"""Tests for the manual POS-link service (ASS-102 v0).

Covers the POS-vendor-independent slice: linking a receipt/order to a visit,
the link guards (voided visit, missing reference, duplicate receipt), the
canonical ``pos_order_linked`` (+ ``payment_refunded`` on refund) emission, and
voiding. CSV import + reconciliation are held (OQ-C) and not exercised here.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEntry
from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account, Role
from apps.pos_lite.models import PaymentStatus, PosOrder, PosOrderStatus, ReconciliationStatus
from apps.pos_lite.services import link_pos_order, void_pos_order
from apps.visit.models import VisitRecord
from apps.visit.services import record_visit, void_visit

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _visit(operator: Account, fan: Account) -> VisitRecord:
    """Record a manual visit to link a POS order against."""
    return record_visit(fan=fan, visited_at=timezone.now(), actor=operator)


def test_link_creates_order_and_emits_event() -> None:
    """A manual link stores the row and emits the canonical pos_order_linked."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)

    order = link_pos_order(
        visit=visit,
        actor=op,
        pos_receipt_no="R-1",
        payment_status=PaymentStatus.PAID.value,
        payment_method="card",
        amount=Decimal("12000.00"),
        pos_vendor_name="toss_place",
    )

    assert order.pos_receipt_no == "R-1"
    assert order.payment_status == "paid"
    assert order.link_method == "manual"
    assert order.reconciliation_status == ReconciliationStatus.UNMATCHED.value

    event = EventRecord.objects.get(event_name=EventName.POS_ORDER_LINKED.value)
    assert event.visit_id == str(visit.id)
    assert event.payload["link_method"] == "manual"
    assert event.payload["payment_status"] == "paid"
    assert event.payload["linked_confidence"] == "manual"
    assert event.payload["payment_amount"] == "12000.00"
    assert event.payload["payment_method"] == "card"
    assert event.ids["pos_receipt_no"] == "R-1"


def test_link_requires_receipt_or_order() -> None:
    """A link carrying neither a receipt nor an order number is rejected."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)

    with pytest.raises(ValueError, match="receipt number or an order number"):
        link_pos_order(visit=visit, actor=op)


def test_link_to_voided_visit_rejected() -> None:
    """A POS order cannot be linked to a voided visit."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    void_visit(record=visit, reason="duplicate", actor=op)

    with pytest.raises(ValueError, match="voided visit"):
        link_pos_order(visit=visit, actor=op, pos_receipt_no="R-2")


def test_duplicate_active_receipt_rejected() -> None:
    """The same receipt cannot be linked to two active POS orders."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit_a = _visit(op, fan)
    visit_b = _visit(op, fan)
    link_pos_order(visit=visit_a, actor=op, pos_receipt_no="DUP")

    with pytest.raises(ValueError, match="already linked"):
        link_pos_order(visit=visit_b, actor=op, pos_receipt_no="DUP")


def test_void_frees_receipt_for_relink() -> None:
    """Voiding a link releases its receipt so a corrected link can reuse it."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit_a = _visit(op, fan)
    visit_b = _visit(op, fan)
    order = link_pos_order(visit=visit_a, actor=op, pos_receipt_no="FREE")

    void_pos_order(order=order, reason="wrong visit", actor=op)
    # Re-linking the same receipt now succeeds (the void left ``active``).
    relinked = link_pos_order(visit=visit_b, actor=op, pos_receipt_no="FREE")
    assert relinked.status == PosOrderStatus.ACTIVE.value


def test_refund_link_sets_status_and_emits_payment_refunded() -> None:
    """A refunded link keeps the refund as a separate status + exclusion event."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)

    order = link_pos_order(
        visit=visit,
        actor=op,
        pos_receipt_no="R-REF",
        payment_status=PaymentStatus.REFUNDED.value,
        refund_reason="customer_request",
    )

    assert order.payment_status == "refunded"
    refund = EventRecord.objects.get(event_name=EventName.PAYMENT_REFUNDED.value)
    assert refund.visit_id == str(visit.id)
    assert refund.payload["refund_type"] == "full"
    assert refund.payload["refund_reason"] == "customer_request"


def test_paid_link_does_not_emit_payment_refunded() -> None:
    """A normal paid link emits no refund event."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    link_pos_order(
        visit=visit, actor=op, pos_receipt_no="R-OK", payment_status=PaymentStatus.PAID.value
    )
    assert not EventRecord.objects.filter(event_name=EventName.PAYMENT_REFUNDED.value).exists()


def test_void_excludes_and_audits() -> None:
    """Voiding flips status + reconciliation_status and writes an audit entry."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    order = link_pos_order(visit=visit, actor=op, pos_order_id="O-1")

    voided = void_pos_order(order=order, reason="entered twice", actor=op)
    assert voided.status == PosOrderStatus.VOIDED.value
    assert voided.reconciliation_status == ReconciliationStatus.EXCLUDED.value
    assert AuditEntry.objects.filter(
        action=AuditAction.POS_ORDER_VOIDED.value, target=str(order.id)
    ).exists()


def test_unknown_payment_status_rejected() -> None:
    """An out-of-domain payment_status is rejected before any write."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    with pytest.raises(ValueError, match="payment_status"):
        link_pos_order(visit=visit, actor=op, pos_receipt_no="R-X", payment_status="bogus")
    assert not PosOrder.objects.exists()


def test_cancelled_emits_payment_refunded_as_cancellation() -> None:
    """A cancelled payment is also a first-class exclusion fact (refund_type)."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    link_pos_order(
        visit=visit,
        actor=op,
        pos_receipt_no="R-CXL",
        payment_status=PaymentStatus.CANCELLED.value,
    )
    refund = EventRecord.objects.get(event_name=EventName.PAYMENT_REFUNDED.value)
    assert refund.payload["refund_type"] == "cancellation"
    # Defaulted (no reason given) to the coded ``other``, never free text.
    assert refund.payload["refund_reason"] == "other"


def test_refund_event_carries_receipt_id_for_attribution() -> None:
    """payment_refunded threads the receipt id so it can be netted per order."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    link_pos_order(
        visit=visit,
        actor=op,
        pos_receipt_no="R-REF2",
        payment_status=PaymentStatus.REFUNDED.value,
        refund_reason="mistake",
    )
    refund = EventRecord.objects.get(event_name=EventName.PAYMENT_REFUNDED.value)
    assert refund.ids["pos_receipt_no"] == "R-REF2"
    assert refund.ids["visit_id"] == str(visit.id)


def test_unknown_refund_reason_rejected() -> None:
    """An out-of-domain refund_reason is rejected before any write."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    with pytest.raises(ValueError, match="refund_reason"):
        link_pos_order(
            visit=visit,
            actor=op,
            pos_receipt_no="R-BR",
            payment_status=PaymentStatus.REFUNDED.value,
            refund_reason="operator_marked",
        )
    assert not PosOrder.objects.exists()


def test_negative_amount_rejected_at_service() -> None:
    """A negative amount is rejected at the service (independent of the API)."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    with pytest.raises(ValueError, match="negative"):
        link_pos_order(visit=visit, actor=op, pos_receipt_no="R-NEG", amount=Decimal("-1"))


def test_default_method_and_vendor_are_omitted_from_event() -> None:
    """Optional keys stay out of the event payload when at default/empty."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    link_pos_order(visit=visit, actor=op, pos_order_id="O-DEF")
    event = EventRecord.objects.get(event_name=EventName.POS_ORDER_LINKED.value)
    assert "payment_method" not in event.payload
    assert "pos_vendor_name" not in event.payload
    assert "payment_amount" not in event.payload


def test_link_writes_audit_entry() -> None:
    """A link writes a POS_ORDER_LINKED audit row for accountability."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    order = link_pos_order(visit=visit, actor=op, pos_receipt_no="R-AUD")
    assert AuditEntry.objects.filter(
        action=AuditAction.POS_ORDER_LINKED.value, target=str(order.id)
    ).exists()
