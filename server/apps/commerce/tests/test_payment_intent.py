"""#4/#2 — 2-phase payment intent (PENDING→PAID / PENDING→FAILED) for checkout.

``create_order`` persists a PENDING order (stock reserved) and COMMITS before it
captures through the gateway OUTSIDE that transaction, so a capture that succeeds
after a DB-commit failure can never bill a customer with no order. On approval the
order transitions PENDING→PAID (+ one settlement ledger row); on a decline it
transitions PENDING→FAILED, restores the reserved stock, and returns a coded 402.

The deterministic mock captures synchronously and approves, so the mock path still
ends PAID and every existing commerce test stays green — these tests prove the new
internal 2-phase structure (an intermediate PENDING at capture time, the FAILED +
restock decline path, idempotent no-double-charge, and the fail-closed head-guard).
"""

from __future__ import annotations

import json

import pytest
from django.test import Client, override_settings

from apps.commerce.models import Order, OrderItem, OrderStatus, Product
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.notification.models import Notification
from apps.payments.models import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentProvider,
)
from config.errors import ErrorCode
from config.payment import (
    ChargeStatus,
    PaymentCharge,
    PaymentGateway,
    PaymentProvenance,
)

pytestmark = pytest.mark.django_db

BASE = "/api/orders"
JSON = "application/json"
GATEWAY_ATTR = "apps.commerce.api.payment_gateway"


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    """Return a test-client headers mapping bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _product(**kwargs: object) -> Product:
    """Create an orderable digital product (no shipping gate involved)."""
    defaults: dict[str, object] = {"type": "digital", "title": "디지털", "price": 5000}
    defaults.update(kwargs)
    creator = Creator.objects.create(handle="stellar", name="별빛")
    defaults.setdefault("creator", creator)
    return Product.objects.create(**defaults)


def _order_body(product: Product, **extra: object) -> str:
    """Serialize a checkout body for ``product`` (digital — no shipping)."""
    body: dict[str, object] = {"product_id": str(product.id), "qty": 1}
    body.update(extra)
    return json.dumps(body)


class _RecordingGateway(PaymentGateway):
    """Approving gateway that records the order's DB status at capture time.

    Used to prove PHASE 1 committed a **PENDING** order BEFORE the PHASE-2 capture
    ran — the capture reads the order back and the test asserts it was PENDING when
    charged, then PAID after the approval transition.
    """

    def __init__(self) -> None:
        """Start with no observed status (populated on the first ``charge``)."""
        self.observed_status: str | None = None
        self.observed_key: str | None = None
        self.charge_calls = 0

    def charge(
        self,
        *,
        order_id: str,
        amount: int,
        currency: str,
        idempotency_key: str | None = None,
    ) -> PaymentCharge:
        """Record the order's status + the passed key, then approve inline."""
        del amount, currency
        self.charge_calls += 1
        self.observed_status = Order.objects.get(id=order_id).status
        self.observed_key = idempotency_key
        return PaymentCharge(
            status=ChargeStatus.APPROVED,
            provider_ref=f"mock_{order_id}",
            provenance=PaymentProvenance.MOCK,
        )


class _DecliningGateway(PaymentGateway):
    """Gateway that declines every capture (simulates a real-PG decline)."""

    def charge(
        self,
        *,
        order_id: str,
        amount: int,
        currency: str,
        idempotency_key: str | None = None,
    ) -> PaymentCharge:
        """Return a FAILED (not-approved) charge — the order must go FAILED."""
        del order_id, amount, currency, idempotency_key
        return PaymentCharge(
            status=ChargeStatus.FAILED,
            provider_ref="",
            provenance=PaymentProvenance.MOCK,
        )


def test_checkout_ends_paid_via_pending_internally(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A normal checkout is PENDING at capture time and ends PAID (2-phase proof)."""
    gateway = _RecordingGateway()
    monkeypatch.setattr(GATEWAY_ATTR, lambda: gateway)
    fan = _fan()
    product = _product(price=7000)

    res = client.post(
        BASE,
        data=_order_body(product, qty=2, idempotency_key="pi-1"),
        content_type=JSON,
        headers=_auth(fan),
    )

    assert res.status_code == 201
    assert res.json()["status"] == OrderStatus.PAID.value
    # PHASE 1 committed a PENDING order that PHASE 2 saw before capturing it.
    assert gateway.charge_calls == 1
    assert gateway.observed_status == OrderStatus.PENDING.value
    # The order's idempotency key is threaded to the gateway so a real PG can dedup.
    assert gateway.observed_key == "pi-1"
    # The order settled: PAID, ``paid_at`` stamped, provider ref recorded, no failure.
    order = Order.objects.get()
    assert order.status == OrderStatus.PAID.value
    assert order.paid_at is not None
    assert order.failed_at is None
    assert order.payment_ref == f"mock_{order.id}"
    # Exactly one succeeded MOCK settlement was ledgered (single capture).
    attempts = list(PaymentAttempt.objects.filter(order=order))
    assert len(attempts) == 1
    assert attempts[0].provider == PaymentProvider.MOCK
    assert attempts[0].status == PaymentAttemptStatus.SUCCEEDED
    assert attempts[0].authorized_amount == 14000
    # Notify fires only on the actually-PAID order.
    assert Notification.objects.filter(recipient=fan, kind="order").count() == 1


def test_declined_charge_fails_order_and_restores_stock(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A declined capture → order FAILED, reserved stock restored, coded 402."""
    monkeypatch.setattr(GATEWAY_ATTR, lambda: _DecliningGateway())
    fan = _fan()
    # stock=2, qty=2 → PHASE 1 reserves the last unit (auto sold_out); the decline
    # must restore it AND re-open the auto-sold-out listing (mirrors cancel restock).
    product = _product(stock=2)

    res = client.post(
        BASE,
        data=_order_body(product, qty=2),
        content_type=JSON,
        headers=_auth(fan),
    )

    assert res.status_code == 402
    assert res.json()["code"] == ErrorCode.PAYMENT_DECLINED.value
    # The order is durably FAILED (not left dangling PENDING), ``failed_at`` stamped.
    order = Order.objects.get()
    assert order.status == OrderStatus.FAILED.value
    assert order.failed_at is not None
    assert order.paid_at is None
    # Reserved stock was restored and the auto sold-out was cleared — no leaked unit.
    product.refresh_from_db()
    assert product.stock == 2
    assert product.sold_out is False
    # A failed order settles nothing and notifies no one.
    assert PaymentAttempt.objects.filter(order=order).count() == 0
    assert Notification.objects.filter(recipient=fan, kind="order").count() == 0


def test_idempotent_retry_returns_same_order_without_second_charge(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A retry with the same key returns the original order, never a second charge."""
    gateway = _RecordingGateway()
    monkeypatch.setattr(GATEWAY_ATTR, lambda: gateway)
    fan = _fan()
    product = _product(price=1000)
    body = _order_body(product, idempotency_key="pi-retry")

    first = client.post(BASE, data=body, content_type=JSON, headers=_auth(fan))
    assert first.status_code == 201
    order_id = first.json()["id"]

    again = client.post(BASE, data=body, content_type=JSON, headers=_auth(fan))
    assert again.status_code == 200
    assert again.json()["id"] == order_id
    # No duplicate order, exactly one capture, exactly one settlement row.
    assert Order.objects.filter(buyer=fan).count() == 1
    assert gateway.charge_calls == 1
    assert PaymentAttempt.objects.filter(order_id=order_id).count() == 1


@override_settings(ENABLE_MOCK_PAYMENT=False)
def test_require_payment_available_still_fails_closed(client: Client) -> None:
    """With the mock flag off, checkout fails closed (503) and mints nothing.

    The head-guard precedes PHASE 1, so no PENDING order, line, or stock reservation
    is ever created when there is no settleable payment path (ASS-286 preserved).
    """
    fan = _fan()
    product = _product(price=1000, stock=5)
    res = client.post(
        BASE,
        data=_order_body(product),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 503
    assert res.json()["code"] == ErrorCode.PAYMENTS_UNAVAILABLE.value
    assert Order.objects.count() == 0
    assert OrderItem.objects.count() == 0
    product.refresh_from_db()
    assert product.stock == 5
