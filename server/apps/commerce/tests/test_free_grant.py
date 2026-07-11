"""ASS-297 — explicit free-grant flow (commerce orders).

A ``pricing_kind=free`` product is acquired ONLY via ``POST /api/orders/free``
(no payment, provenance=free, amounts 0), and NEVER via the paid checkout. A paid
product — including a price-0 placeholder — is refused on the free path. The free
path drops only the payment gate: the shipping-checkout gate and stock/availability
gates still apply to free goods.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client, override_settings

from apps.commerce.models import Order, OrderItem, Product
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.payments.models import PaymentAttempt, PaymentProvider
from config.errors import ErrorCode
from config.payment import PaymentProvenance, PricingKind

pytestmark = pytest.mark.django_db

PAID = "/api/orders"
FREE = "/api/orders/free"
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
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    """Return test-client headers bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _product(**kwargs: object) -> Product:
    """Create a product (digital by default — no shipping gate)."""
    defaults: dict[str, object] = {"type": "digital", "title": "디지털", "price": 0}
    defaults.update(kwargs)
    creator = Creator.objects.create(handle="stellar", name="별빛")
    defaults.setdefault("creator", creator)
    return Product.objects.create(**defaults)


@override_settings(ENABLE_MOCK_PAYMENT=False)
def test_free_order_grants_without_payment(client: Client) -> None:
    """A free product is acquired with the payment gate OFF — provenance=free, 0원."""
    fan = _fan()
    product = _product(pricing_kind=PricingKind.FREE.value, price=0)
    res = client.post(
        FREE,
        data=json.dumps({"product_id": str(product.id), "qty": 2}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    order = Order.objects.get()
    assert order.payment_provenance == PaymentProvenance.FREE
    assert order.total == 0
    assert order.subtotal == 0
    line = OrderItem.objects.get(order=order)
    assert line.price == 0
    assert line.qty == 2
    attempt = PaymentAttempt.objects.get(order=order)
    assert attempt.provider == PaymentProvider.FREE
    assert attempt.authorized_amount == 0


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_free_path_refuses_a_paid_product(client: Client) -> None:
    """A paid product (even price 0 placeholder) can't be taken via the free path."""
    fan = _fan()
    product = _product(pricing_kind=PricingKind.PAID.value, price=0)
    res = client.post(
        FREE,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 422
    assert res.json()["code"] == ErrorCode.PRICING_NOT_FREE.value
    assert Order.objects.count() == 0


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_paid_path_refuses_a_free_product(client: Client) -> None:
    """A free product can't be bought through the paid checkout (PricingIsFree)."""
    fan = _fan()
    product = _product(pricing_kind=PricingKind.FREE.value, price=0)
    res = client.post(
        PAID,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 422
    assert res.json()["code"] == ErrorCode.PRICING_IS_FREE.value
    assert Order.objects.count() == 0


@override_settings(ENABLE_MOCK_PAYMENT=False, ENABLE_SHIPPING_CHECKOUT=False)
def test_free_goods_still_shipping_gated(client: Client) -> None:
    """Free goods drop the payment gate but NOT the shipping-checkout gate (503)."""
    fan = _fan()
    product = _product(type="goods", pricing_kind=PricingKind.FREE.value, price=0)
    res = client.post(
        FREE,
        data=json.dumps({"product_id": str(product.id), "shipping": SHIPPING}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 503
    assert res.json()["code"] == str(ErrorCode.SHIPPING_CHECKOUT_UNAVAILABLE)
    assert Order.objects.count() == 0


@override_settings(ENABLE_MOCK_PAYMENT=False, ENABLE_SHIPPING_CHECKOUT=True)
def test_free_goods_need_a_complete_address(client: Client) -> None:
    """With shipping on, free goods still require a full delivery address."""
    fan = _fan()
    product = _product(type="goods", pricing_kind=PricingKind.FREE.value, price=0)
    missing = client.post(
        FREE,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert missing.status_code == 422
    assert missing.json()["code"] == ErrorCode.SHIPPING_ADDRESS_REQUIRED.value

    ok = client.post(
        FREE,
        data=json.dumps({"product_id": str(product.id), "shipping": SHIPPING}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert ok.status_code == 201
    assert Order.objects.get().payment_provenance == PaymentProvenance.FREE


@override_settings(ENABLE_MOCK_PAYMENT=False)
def test_free_order_still_stock_gated(client: Client) -> None:
    """A free product that is sold out is refused just like a paid one."""
    fan = _fan()
    product = _product(pricing_kind=PricingKind.FREE.value, price=0, stock=0)
    res = client.post(
        FREE,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 422
    assert res.json()["code"] == ErrorCode.OUT_OF_STOCK.value
    assert Order.objects.count() == 0
