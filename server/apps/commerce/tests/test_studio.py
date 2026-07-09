"""Tests for the commerce studio (owner catalog write) + public 19+/visibility gate.

Covers owner-guard 403 / auth 401, create+list including draft/status, owner-scoped
update/delete (404 for a non-owner, 422 for order history), and the consumer
``list_products`` excluding draft/hidden and gated adult (R3 gated features).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client, override_settings

from apps.commerce.models import Order, OrderItem, OrderStatus, Product
from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
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


def test_studio_requires_auth_401(client: Client) -> None:
    assert client.get(STUDIO).status_code in {401, 403}


def test_studio_requires_creator_owner_403(client: Client) -> None:
    fan = Account.objects.create(role=Role.FAN.value)  # operates no creator
    assert client.get(STUDIO, headers=_auth(fan)).status_code == 403
    res = _post(
        client, STUDIO, {"type": "goods", "title": "x", "price": 1000}, headers=_auth(fan)
    )
    assert res.status_code == 403


def test_studio_create_and_owner_list_includes_draft(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(
        client,
        STUDIO,
        {"type": "goods", "title": "굿즈", "price": 15000, "status": "draft"},
        headers=_auth(owner),
    )
    assert res.status_code == 201
    assert res.json()["status"] == "draft"
    listed = client.get(STUDIO, headers=_auth(owner)).json()
    assert any(p["status"] == "draft" for p in listed)


def test_studio_create_invalid_type_is_422(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(
        client, STUDIO, {"type": "bogus", "title": "x", "price": 0}, headers=_auth(owner)
    )
    assert res.status_code == 422


def test_public_list_excludes_draft_and_hidden(client: Client) -> None:
    _owner, creator = _owner_with_creator()
    for title, status in (("공개", "selling"), ("초안", "draft"), ("숨김", "hidden")):
        Product.objects.create(
            creator=creator, type="goods", title=title, price=1000, status=status
        )
    titles = {p["title"] for p in client.get("/api/products").json()["items"]}
    assert "공개" in titles
    assert "초안" not in titles
    assert "숨김" not in titles


@override_settings(ENABLE_ADULT_CONTENT=False)
def test_public_list_excludes_adult_when_flag_off(client: Client) -> None:
    _owner, creator = _owner_with_creator()
    Product.objects.create(
        creator=creator, type="goods", title="성인", price=1000, adult_only=True
    )
    titles = {p["title"] for p in client.get("/api/products").json()["items"]}
    assert "성인" not in titles


@override_settings(ENABLE_ADULT_CONTENT=True)
def test_public_list_shows_adult_only_to_verified(client: Client) -> None:
    _owner, creator = _owner_with_creator()
    Product.objects.create(
        creator=creator, type="goods", title="성인", price=1000, adult_only=True
    )
    verified = Account.objects.create(
        role=Role.FAN.value, adult_verified=True, kyc_status=KycStatus.VERIFIED.value
    )
    listed = client.get("/api/products", headers=_auth(verified)).json()["items"]
    shown = {r["title"] for r in listed}
    assert "성인" in shown
    # Anonymous still sees nothing.
    assert "성인" not in {p["title"] for p in client.get("/api/products").json()["items"]}


def test_studio_update_and_delete_scoped_to_owner(client: Client) -> None:
    owner, creator = _owner_with_creator()
    other = Account.objects.create(role=Role.FAN.value)
    Creator.objects.create(handle="other", name="다른", owner=other)
    prod = Product.objects.create(creator=creator, type="goods", title="원본", price=1000)

    # A different creator-owner cannot patch/delete it (404, owner-scoped).
    assert (
        _patch(client, f"{STUDIO}/{prod.id}", {"title": "해킹"}, headers=_auth(other)).status_code
        == 404
    )
    assert client.delete(f"{STUDIO}/{prod.id}", headers=_auth(other)).status_code == 404

    # The owner can update and then delete.
    patched = _patch(
        client, f"{STUDIO}/{prod.id}", {"title": "수정", "status": "hidden"}, headers=_auth(owner)
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "수정"
    assert patched.json()["status"] == "hidden"
    deleted = client.delete(f"{STUDIO}/{prod.id}", headers=_auth(owner))
    assert deleted.status_code == 200
    assert not Product.objects.filter(id=prod.id).exists()


def test_studio_delete_product_with_order_history_is_422(client: Client) -> None:
    owner, creator = _owner_with_creator()
    prod = Product.objects.create(creator=creator, type="goods", title="히스토리", price=1000)
    buyer = Account.objects.create(role=Role.FAN.value)
    order = Order.objects.create(buyer=buyer)
    OrderItem.objects.create(
        order=order, product=prod, title=prod.title, item_type=prod.type, qty=1, price=prod.price
    )

    res = client.delete(f"{STUDIO}/{prod.id}", headers=_auth(owner))
    assert res.status_code == 422
    assert res.json()["code"] == "ProductHasOrders"
    assert Product.objects.filter(id=prod.id).exists()  # not deleted; history preserved

    # A product with no order history still deletes as before.
    fresh = Product.objects.create(creator=creator, type="goods", title="새상품", price=500)
    res2 = client.delete(f"{STUDIO}/{fresh.id}", headers=_auth(owner))
    assert res2.status_code == 200
    assert not Product.objects.filter(id=fresh.id).exists()


def _order_item(buyer: Account, product: Product, qty: int, status: str = "paid") -> OrderItem:
    """A one-line order for ``product`` at ``qty``, with the given order ``status``."""
    order = Order.objects.create(buyer=buyer, status=status)
    return OrderItem.objects.create(
        order=order,
        product=product,
        title=product.title,
        item_type=product.type,
        qty=qty,
        price=product.price,
    )


def test_studio_list_products_sold_sums_qty_excluding_cancelled(client: Client) -> None:
    """``sold`` (ASS-264) = total qty across non-cancelled orders; cancelled excluded."""
    owner, creator = _owner_with_creator()
    product = Product.objects.create(creator=creator, type="goods", title="굿즈", price=1000)
    buyer = Account.objects.create(role=Role.FAN.value)

    _order_item(buyer, product, qty=2)
    _order_item(buyer, product, qty=3)
    _order_item(buyer, product, qty=10, status=OrderStatus.CANCELLED.value)

    listed = client.get(STUDIO, headers=_auth(owner)).json()
    row = next(p for p in listed if p["id"] == str(product.id))
    assert row["sold"] == 5  # 2 + 3; the cancelled order's qty=10 is excluded


def test_studio_new_product_sold_is_zero(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    created = _post(
        client, STUDIO, {"type": "goods", "title": "새상품", "price": 500}, headers=_auth(owner)
    )
    assert created.json()["sold"] == 0


def test_studio_list_products_sold_isolated_from_other_owner(client: Client) -> None:
    """Another creator's order activity never leaks into this owner's ``sold`` counts."""
    owner, creator = _owner_with_creator("stellar")
    _other_owner, other_creator = _owner_with_creator("nova")
    my_product = Product.objects.create(creator=creator, type="goods", title="내상품", price=1000)
    other_product = Product.objects.create(
        creator=other_creator, type="goods", title="타인상품", price=1000
    )
    buyer = Account.objects.create(role=Role.FAN.value)
    _order_item(buyer, other_product, qty=7)

    listed = client.get(STUDIO, headers=_auth(owner)).json()
    assert {p["id"] for p in listed} == {str(my_product.id)}
    assert listed[0]["sold"] == 0
