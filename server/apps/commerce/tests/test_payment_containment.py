"""ASS-286 — payment containment (commerce).

With ``ENABLE_MOCK_PAYMENT`` off (production posture: no real PG wired), order
creation must fail closed with a coded 503 and mint **nothing** — no false PAID
order, no line item, no stock decrement, no "order received" notification. The
guard sits before every side effect, including the idempotency replay, so a
supplied ``idempotency_key`` can never surface a prior 200 either.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client, override_settings

from apps.commerce.models import Order, OrderItem, Product
from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair
from apps.notification.models import Notification
from config.errors import ErrorCode

pytestmark = pytest.mark.django_db

BASE = "/api/orders"
JSON = "application/json"
SHIPPING = {
    "recipient_name": "받는이",
    "recipient_phone": "010-1234-5678",
    "postal_code": "06236",
    "address1": "서울시 강남구 테헤란로 1",
    "address2": "101동 1001호",
}


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(
        role=Role.FAN.value, kyc_status=KycStatus.VERIFIED.value
    )


def _auth(account: Account) -> dict[str, str]:
    """Return a test-client headers mapping bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _product(**kwargs: object) -> Product:
    """Create an orderable physical product (would succeed but for the gate)."""
    defaults: dict[str, object] = {"type": "goods", "title": "굿즈", "price": 10000}
    defaults.update(kwargs)
    creator = Creator.objects.create(handle="stellar", name="별빛")
    defaults.setdefault("creator", creator)
    return Product.objects.create(**defaults)


def _order_body(product: Product, **extra: object) -> str:
    body: dict[str, object] = {
        "product_id": str(product.id),
        "qty": 1,
        "shipping": SHIPPING,
    }
    body.update(extra)
    return json.dumps(body)


@override_settings(ENABLE_MOCK_PAYMENT=False)
def test_create_order_fails_closed_and_mints_nothing(client: Client) -> None:
    """mock off → 503 PaymentsUnavailable, zero side effects."""
    fan = _fan()
    product = _product(price=18000, stock=5)
    res = client.post(
        BASE, data=_order_body(product, qty=2), content_type=JSON, headers=_auth(fan)
    )
    assert res.status_code == 503
    assert res.json()["code"] == str(ErrorCode.PAYMENTS_UNAVAILABLE)
    assert Order.objects.count() == 0
    assert OrderItem.objects.count() == 0
    assert Notification.objects.count() == 0
    product.refresh_from_db()
    assert product.stock == 5


@override_settings(ENABLE_MOCK_PAYMENT=False)
def test_idempotency_replay_also_fails_closed(client: Client) -> None:
    """The guard precedes the idempotency lookup — a key never yields a prior 200."""
    fan = _fan()
    product = _product(price=1000)
    res = client.post(
        BASE,
        data=_order_body(product, idempotency_key="k1"),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 503
    assert Order.objects.count() == 0


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_create_order_succeeds_when_mock_enabled(client: Client) -> None:
    """mock on (dev/test) → unchanged: the explicit mock success still works."""
    fan = _fan()
    product = _product(price=1000)
    res = client.post(
        BASE, data=_order_body(product), content_type=JSON, headers=_auth(fan)
    )
    assert res.status_code == 201
    assert Order.objects.count() == 1
