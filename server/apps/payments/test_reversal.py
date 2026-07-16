"""#3 (BLOCKER-seam) — reversal (void/refund) ledger for a settled charge.

A fan cancel / operator refund-accept cancels + restocks a settled order while money
never moves (mock). These tests pin the seam that lets a real PG later reconcile: the
reversal is routed through the gateway's (mock) void/refund op and recorded as an
append-only :class:`~apps.payments.models.PaymentReversal` tied to the settlement it
reverses — succeeded on approve, failed on decline, never double-recorded on a repeat
cancel/refund-accept, and immutable once written. An order with no real capture (a
free grant / unsettled order) records nothing.
"""

from __future__ import annotations

import json
import uuid

import pytest
from django.db import IntegrityError, transaction
from django.test import Client, override_settings

from apps.commerce.models import (
    Order,
    OrderItem,
    OrderStatus,
    Product,
    RefundRequest,
    RefundStatus,
)
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.payments.models import (
    AppendOnlyViolation,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentProvider,
    PaymentReversal,
    PaymentReversalStatus,
)
from apps.payments.services import record_mock_reversal
from config.payment import ChargeStatus, PaymentProvenance, PaymentRefund

pytestmark = pytest.mark.django_db

ORDERS = "/api/orders"
OPS_REFUNDS = "/api/ops/refunds"
JSON = "application/json"


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def _operator() -> Account:
    """Create an operator account."""
    return Account.objects.create(role=Role.OPERATOR.value)


def _auth(account: Account) -> dict[str, str]:
    """Return test-client headers bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _product(*, price: int = 5000) -> Product:
    """Create an orderable digital product (no shipping gate involved)."""
    creator = Creator.objects.create(handle=f"c{uuid.uuid4().hex[:8]}", name="크리에이터")
    return Product.objects.create(
        type="digital", title="디지털", price=price, creator=creator
    )


def _settlement(order: Order, *, amount: int) -> PaymentAttempt:
    """Create a succeeded MOCK settlement attempt for ``order`` (the reversed capture)."""
    return PaymentAttempt.objects.create(
        order=order,
        provider=PaymentProvider.MOCK,
        provider_txn_id=f"mock_{order.id}",
        authorized_amount=amount,
        currency="KRW",
        status=PaymentAttemptStatus.SUCCEEDED,
    )


# --- wiring: cancel / refund-accept record a succeeded reversal -------------- #


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_cancel_settled_order_records_succeeded_reversal(client: Client) -> None:
    """Cancelling a settled order reverses the capture: one succeeded, linked reversal."""
    fan = _fan()
    product = _product(price=7000)
    res = client.post(
        ORDERS,
        data=json.dumps({"product_id": str(product.id), "qty": 2}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    order = Order.objects.get()
    attempt = PaymentAttempt.objects.get(order=order, provider=PaymentProvider.MOCK)

    cancelled = client.post(
        f"{ORDERS}/{order.id}/cancel", content_type=JSON, headers=_auth(fan)
    )
    assert cancelled.status_code == 200

    reversal = PaymentReversal.objects.get(original_attempt=attempt)
    assert reversal.status == PaymentReversalStatus.SUCCEEDED
    assert reversal.provider == PaymentProvider.MOCK
    assert reversal.amount == 14000
    assert reversal.currency == "KRW"
    assert reversal.reversal_ref == f"mock_reversal_{order.id}"
    assert reversal.reason == "order_cancelled"


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_refund_accept_settled_order_records_succeeded_reversal(client: Client) -> None:
    """Operator-accepting a refund on a settled order records a linked succeeded reversal."""
    fan = _fan()
    product = _product(price=9000)
    res = client.post(
        ORDERS,
        data=json.dumps({"product_id": str(product.id), "qty": 1}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    order = Order.objects.get()
    attempt = PaymentAttempt.objects.get(order=order, provider=PaymentProvider.MOCK)
    # Move the settled order into a refundable state and open a refund request.
    Order.objects.filter(id=order.id).update(status=OrderStatus.SHIPPING.value)
    refund = RefundRequest.objects.create(
        order=order, reason="단순 변심", status=RefundStatus.REQUESTED.value
    )

    accepted = client.post(
        f"{OPS_REFUNDS}/{refund.id}/accept",
        content_type=JSON,
        headers=_auth(_operator()),
    )
    assert accepted.status_code == 200

    reversal = PaymentReversal.objects.get(original_attempt=attempt)
    assert reversal.status == PaymentReversalStatus.SUCCEEDED
    assert reversal.amount == 9000
    assert reversal.reason == "refund_accepted"
    order.refresh_from_db()
    assert order.status == OrderStatus.CANCELLED.value


# --- idempotency: a repeat cancel/refund-accept does not double-record ------- #


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_duplicate_cancel_does_not_double_record(client: Client) -> None:
    """A second cancel (422) never writes a second reversal for the same capture."""
    fan = _fan()
    product = _product(price=5000)
    res = client.post(
        ORDERS,
        data=json.dumps({"product_id": str(product.id), "qty": 1}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    order = Order.objects.get()
    attempt = PaymentAttempt.objects.get(order=order, provider=PaymentProvider.MOCK)

    first = client.post(
        f"{ORDERS}/{order.id}/cancel", content_type=JSON, headers=_auth(fan)
    )
    assert first.status_code == 200
    second = client.post(
        f"{ORDERS}/{order.id}/cancel", content_type=JSON, headers=_auth(fan)
    )
    assert second.status_code == 422

    assert PaymentReversal.objects.filter(original_attempt=attempt).count() == 1


def test_second_succeeded_reversal_per_attempt_is_rejected() -> None:
    """The DB seals the idempotency guard: two succeeded reversals per attempt fail."""
    fan = _fan()
    order = Order.objects.create(buyer=fan, total=5000, status=OrderStatus.PAID.value)
    attempt = _settlement(order, amount=5000)
    approved = PaymentRefund(ChargeStatus.APPROVED, "ref1", PaymentProvenance.MOCK)
    record_mock_reversal(original_attempt=attempt, refund=approved, amount=5000)
    with pytest.raises(IntegrityError), transaction.atomic():
        record_mock_reversal(original_attempt=attempt, refund=approved, amount=5000)


# --- gateway outcome mapping ------------------------------------------------ #


def test_mock_decline_records_failed_reversal() -> None:
    """A declined gateway reversal is persisted ``failed`` (not succeeded)."""
    fan = _fan()
    order = Order.objects.create(buyer=fan, total=5000, status=OrderStatus.PAID.value)
    attempt = _settlement(order, amount=5000)
    declined = PaymentRefund(ChargeStatus.FAILED, "", PaymentProvenance.MOCK)

    reversal = record_mock_reversal(
        original_attempt=attempt, refund=declined, amount=5000, reason="order_cancelled"
    )
    assert reversal.status == PaymentReversalStatus.FAILED
    # A failed reversal does not trip the succeeded-only unique guard.
    assert not attempt.reversals.filter(
        status=PaymentReversalStatus.SUCCEEDED.value
    ).exists()


def test_pending_gateway_reversal_records_pending() -> None:
    """A pending (out-of-band) gateway reversal is persisted ``pending``."""
    fan = _fan()
    order = Order.objects.create(buyer=fan, total=5000, status=OrderStatus.PAID.value)
    attempt = _settlement(order, amount=5000)
    pending = PaymentRefund(ChargeStatus.PENDING, "", PaymentProvenance.MOCK)

    reversal = record_mock_reversal(
        original_attempt=attempt, refund=pending, amount=5000
    )
    assert reversal.status == PaymentReversalStatus.PENDING


# --- immutability ----------------------------------------------------------- #


def test_reversal_is_append_only() -> None:
    """A persisted reversal cannot be mutated — re-saving raises AppendOnlyViolation."""
    fan = _fan()
    order = Order.objects.create(buyer=fan, total=5000, status=OrderStatus.PAID.value)
    attempt = _settlement(order, amount=5000)
    reversal = record_mock_reversal(
        original_attempt=attempt,
        refund=PaymentRefund(ChargeStatus.APPROVED, "ref", PaymentProvenance.MOCK),
        amount=5000,
    )

    reversal.status = PaymentReversalStatus.FAILED.value
    with pytest.raises(AppendOnlyViolation):
        reversal.save()

    reversal.refresh_from_db()
    assert reversal.status == PaymentReversalStatus.SUCCEEDED


# --- guard: no real capture => no reversal ---------------------------------- #


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_cancel_free_grant_order_records_no_reversal(client: Client) -> None:
    """Cancelling an order with only a FREE grant reverses nothing (no capture moved)."""
    fan = _fan()
    order = Order.objects.create(buyer=fan, total=0, status=OrderStatus.PAID.value)
    OrderItem.objects.create(
        order=order, title="무료", item_type="digital", qty=1, price=0
    )
    PaymentAttempt.objects.create(
        order=order,
        provider=PaymentProvider.FREE,
        authorized_amount=0,
        status=PaymentAttemptStatus.SUCCEEDED,
    )

    cancelled = client.post(
        f"{ORDERS}/{order.id}/cancel", content_type=JSON, headers=_auth(fan)
    )
    assert cancelled.status_code == 200
    assert PaymentReversal.objects.filter(original_attempt__order=order).count() == 0
    order.refresh_from_db()
    assert order.status == OrderStatus.CANCELLED.value
