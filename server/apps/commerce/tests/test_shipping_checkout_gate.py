"""ASS-287 A-1 — delivery (shipping) checkout gate.

While ``ENABLE_SHIPPING_CHECKOUT`` is off (the default in base/prod/demo, until
the postal-shipping privacy policy is approved), a physical (goods) order is
refused with a coded 503 so NO recipient name/phone/address PII is collected.
Non-goods orders (which carry no address) are unaffected, and turning the flag
on restores the flow. Payment is enabled here so the gate under test is the
shipping one, not the payment containment (ASS-286).
"""

from __future__ import annotations

import json

import pytest
from django.test import Client, override_settings

from apps.commerce.models import Order, Product
from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair
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
    return Account.objects.create(
        role=Role.FAN.value, kyc_status=KycStatus.VERIFIED.value
    )


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _product(**kwargs: object) -> Product:
    defaults: dict[str, object] = {"type": "goods", "title": "굿즈", "price": 10000}
    defaults.update(kwargs)
    defaults.setdefault("creator", Creator.objects.create(handle="stellar", name="별빛"))
    return Product.objects.create(**defaults)


@override_settings(ENABLE_MOCK_PAYMENT=True, ENABLE_SHIPPING_CHECKOUT=False)
def test_goods_order_refused_when_shipping_off(client: Client) -> None:
    """goods + shipping off → 503 ShippingCheckoutUnavailable, nothing minted."""
    fan = _fan()
    product = _product(type="goods", price=10000)
    res = client.post(
        BASE,
        data=json.dumps(
            {"product_id": str(product.id), "qty": 1, "shipping": SHIPPING}
        ),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 503
    assert res.json()["code"] == str(ErrorCode.SHIPPING_CHECKOUT_UNAVAILABLE)
    assert Order.objects.count() == 0


@override_settings(ENABLE_MOCK_PAYMENT=True, ENABLE_SHIPPING_CHECKOUT=True)
def test_goods_order_allowed_when_shipping_on(client: Client) -> None:
    """goods + shipping on → 201 (the flow is restored)."""
    fan = _fan()
    product = _product(type="goods", price=10000)
    res = client.post(
        BASE,
        data=json.dumps(
            {"product_id": str(product.id), "qty": 1, "shipping": SHIPPING}
        ),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    assert Order.objects.count() == 1


@override_settings(ENABLE_MOCK_PAYMENT=True, ENABLE_SHIPPING_CHECKOUT=False)
def test_digital_order_unaffected_by_shipping_gate(client: Client) -> None:
    """A non-goods (digital) order carries no address → unaffected by the gate."""
    fan = _fan()
    product = _product(type="digital", price=1000)
    res = client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id), "qty": 1}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    assert Order.objects.count() == 1
