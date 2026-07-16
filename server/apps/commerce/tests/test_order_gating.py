"""19+/visibility gating regressions for the order flow and single product fetch.

Codex R3 + code-reviewer: ``create_order`` must go through the gated consumer
queryset (draft/hidden/gated-adult 404, and only a live ``selling`` listing
orderable), and ``get_product`` must 404 a draft/hidden/gated-adult listing (no
existence leak) — mirroring the post read gate (see ``content/tests/test_adult_gating``).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client, override_settings

from apps.commerce.models import Order, Product
from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

ORDERS = "/api/orders"
PRODUCTS = "/api/products"
JSON = "application/json"


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _fan() -> Account:
    return Account.objects.create(
        role=Role.FAN.value, kyc_status=KycStatus.VERIFIED.value
    )


def _verified_fan() -> Account:
    return Account.objects.create(
        role=Role.FAN.value, adult_verified=True, kyc_status=KycStatus.VERIFIED.value
    )


def _creator() -> Creator:
    return Creator.objects.create(handle="stellar", name="별빛")


def _product(**kwargs: Any) -> Product:
    defaults: dict[str, Any] = {"type": "goods", "title": "굿즈", "price": 1000}
    defaults.update(kwargs)
    defaults.setdefault("creator", _creator())
    return Product.objects.create(**defaults)


# Delivery address for goods orders (required since R5-W1A); the gating tests use
# goods products, so every order body carries it.
SHIPPING = {
    "recipient_name": "받는이",
    "recipient_phone": "010-1234-5678",
    "postal_code": "06236",
    "address1": "서울시 강남구 테헤란로 1",
    "address2": "101동 1001호",
}


def _order(client: Client, product_id: Any, account: Account) -> Any:
    return client.post(
        ORDERS,
        data=json.dumps({"product_id": str(product_id), "shipping": SHIPPING}),
        content_type=JSON,
        headers=_auth(account),
    )


# --- create_order gating (Codex BLOCKER #1) ---------------------------------- #


@override_settings(ENABLE_ADULT_CONTENT=False)
def test_order_adult_product_404_when_flag_off(client: Client) -> None:
    """An adult listing can't be ordered while the flag is off — even by a verified fan."""
    product = _product(title="성인", adult_only=True)
    res = _order(client, product.id, _verified_fan())
    assert res.status_code == 404
    assert Order.objects.count() == 0


@override_settings(ENABLE_ADULT_CONTENT=True)
def test_order_adult_product_404_for_unverified_when_flag_on(client: Client) -> None:
    """With the flag on, an unverified fan still 404s (no existence leak) on order."""
    product = _product(title="성인", adult_only=True)
    res = _order(client, product.id, _fan())
    assert res.status_code == 404
    assert Order.objects.count() == 0


@override_settings(ENABLE_ADULT_CONTENT=True)
def test_order_adult_product_ok_for_verified_when_flag_on(client: Client) -> None:
    """A verified fan can order an adult listing when the flag is on."""
    product = _product(title="성인", adult_only=True)
    res = _order(client, product.id, _verified_fan())
    assert res.status_code == 201


def test_order_draft_product_is_404(client: Client) -> None:
    """A draft (owner-only) listing 404s on order rather than slipping past the gate."""
    product = _product(title="초안", status="draft")
    res = _order(client, product.id, _fan())
    assert res.status_code == 404
    assert Order.objects.count() == 0


def test_order_hidden_product_is_404(client: Client) -> None:
    """A hidden (owner-only) listing 404s on order."""
    product = _product(title="숨김", status="hidden")
    res = _order(client, product.id, _fan())
    assert res.status_code == 404
    assert Order.objects.count() == 0


def test_order_soldout_status_product_is_422(client: Client) -> None:
    """A 'soldout'-status listing stays visible but is not orderable (only 'selling' is)."""
    product = _product(title="품절", status="soldout")
    res = _order(client, product.id, _fan())
    assert res.status_code == 422
    assert Order.objects.count() == 0


def test_order_selling_product_still_succeeds(client: Client) -> None:
    """The default 'selling' listing remains orderable (no regression to the smoke path)."""
    product = _product(title="공개")  # status defaults to 'selling'
    res = _order(client, product.id, _fan())
    assert res.status_code == 201


# --- get_product single-fetch gating (code-reviewer #6) ---------------------- #


def test_get_product_draft_is_404(client: Client) -> None:
    product = _product(title="초안", status="draft")
    assert client.get(f"{PRODUCTS}/{product.id}").status_code == 404


def test_get_product_hidden_is_404(client: Client) -> None:
    product = _product(title="숨김", status="hidden")
    assert client.get(f"{PRODUCTS}/{product.id}").status_code == 404


@override_settings(ENABLE_ADULT_CONTENT=False)
def test_get_product_adult_is_404_when_flag_off(client: Client) -> None:
    """Direct single fetch of an adult listing 404s while the flag is off (no leak)."""
    product = _product(title="성인", adult_only=True)
    got = client.get(f"{PRODUCTS}/{product.id}", headers=_auth(_verified_fan()))
    assert got.status_code == 404


@override_settings(ENABLE_ADULT_CONTENT=True)
def test_get_product_adult_ok_for_verified_when_flag_on(client: Client) -> None:
    product = _product(title="성인", adult_only=True)
    got = client.get(f"{PRODUCTS}/{product.id}", headers=_auth(_verified_fan()))
    assert got.status_code == 200
    assert got.json()["is_adult"] is True
