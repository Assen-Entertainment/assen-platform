"""Studio (owner) support for ``pricing_kind`` on products (ASS-297).

The owner studio can mark a product genuinely free (``pricing_kind="free"``), with a
coherence guard: "free" and a nonzero price are mutually exclusive (422
``PricingFreeRequiresZeroPrice``). An unknown ``pricing_kind`` is a schema 422, and
an omitted value defaults to "paid" (a price-0 row is a placeholder, never free).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client

from apps.commerce.models import Product
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

STUDIO = "/api/studio/products"
JSON = "application/json"


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _owner_with_creator(handle: str = "stellar") -> tuple[Account, Creator]:
    account = Account.objects.create(role=Role.FAN.value)
    creator = Creator.objects.create(handle=handle, name="별빛", owner=account)
    return account, creator


def _post(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.post(path, data=json.dumps(body), content_type=JSON, **extra)


def _patch(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.patch(path, data=json.dumps(body), content_type=JSON, **extra)


def test_create_free_product_with_zero_price_is_201(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(
        client,
        STUDIO,
        {"type": "goods", "title": "무료굿즈", "price": 0, "pricing_kind": "free"},
        headers=_auth(owner),
    )
    assert res.status_code == 201
    assert res.json()["pricing_kind"] == "free"
    product = Product.objects.get(id=res.json()["id"])
    assert product.pricing_kind == "free"


def test_create_free_product_with_nonzero_price_is_422(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(
        client,
        STUDIO,
        {"type": "goods", "title": "모순", "price": 5000, "pricing_kind": "free"},
        headers=_auth(owner),
    )
    assert res.status_code == 422
    assert res.json()["code"] == "PricingFreeRequiresZeroPrice"
    assert Product.objects.count() == 0  # nothing created on the coherence failure


def test_update_paid_product_to_free_without_zeroing_price_is_422(client: Client) -> None:
    owner, creator = _owner_with_creator()
    product = Product.objects.create(
        creator=creator, type="goods", title="유료", price=3000
    )
    res = _patch(
        client, f"{STUDIO}/{product.id}", {"pricing_kind": "free"}, headers=_auth(owner)
    )
    assert res.status_code == 422
    assert res.json()["code"] == "PricingFreeRequiresZeroPrice"
    product.refresh_from_db()
    assert product.pricing_kind == "paid"  # unchanged
    assert product.price == 3000


def test_update_to_free_and_zero_price_same_patch_is_200(client: Client) -> None:
    owner, creator = _owner_with_creator()
    product = Product.objects.create(
        creator=creator, type="goods", title="유료", price=3000
    )
    res = _patch(
        client,
        f"{STUDIO}/{product.id}",
        {"pricing_kind": "free", "price": 0},
        headers=_auth(owner),
    )
    assert res.status_code == 200
    assert res.json()["pricing_kind"] == "free"
    product.refresh_from_db()
    assert product.pricing_kind == "free"
    assert product.price == 0


def test_create_invalid_pricing_kind_is_422(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(
        client,
        STUDIO,
        {"type": "goods", "title": "이상", "price": 0, "pricing_kind": "bogus"},
        headers=_auth(owner),
    )
    assert res.status_code == 422  # schema validation rejects the unknown value
    assert Product.objects.count() == 0


def test_create_default_pricing_kind_is_paid(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(
        client,
        STUDIO,
        {"type": "goods", "title": "기본", "price": 1000},
        headers=_auth(owner),
    )
    assert res.status_code == 201
    assert res.json()["pricing_kind"] == "paid"
    product = Product.objects.get(id=res.json()["id"])
    assert product.pricing_kind == "paid"
