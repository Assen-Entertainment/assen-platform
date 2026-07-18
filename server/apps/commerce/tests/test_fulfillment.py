"""Tests for the order fulfillment FSM (#11 — mock/manual shipping, no money moves).

Covers the load-bearing rules of the creator/operator fulfillment lifecycle:
PAID → SHIPPING (creator/operator, carrier + tracking) → COMPLETED, the leak-free
authorization (a buyer or a different creator cannot transition another's order), the
illegal-transition rowcount gate (ship a completed/cancelled order → 422), the
digital-delivery shortcut (a digital-only order completes straight from PAID without a
shipping step), and the creator order queue (``/studio/orders`` scoped to the caller's
own creator, refused to a plain fan).
"""

from __future__ import annotations

import json

import pytest
from django.test import Client

from apps.commerce.models import Order, OrderItem, OrderStatus, Product
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

BASE = "/api/orders"
STUDIO_ORDERS = "/api/studio/orders"
JSON = "application/json"

SHIP_BODY = {"carrier": "CJ대한통운", "tracking_number": "1234567890"}


def _fan() -> Account:
    """Create a fan account (buyer / no creator profile)."""
    return Account.objects.create(role=Role.FAN.value)


def _operator() -> Account:
    """Create an operator account (staff role)."""
    return Account.objects.create(role=Role.OPERATOR.value)


def _auth(account: Account) -> dict[str, str]:
    """Return a test-client headers mapping bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _owner_with_creator(handle: str) -> tuple[Account, Creator]:
    """Create a fan account that operates a fresh creator profile."""
    account = Account.objects.create(role=Role.FAN.value)
    creator = Creator.objects.create(handle=handle, name="크리에이터", owner=account)
    return account, creator


def _product(creator: Creator, *, product_type: str = "goods", price: int = 10000) -> Product:
    """Create a product owned by ``creator``."""
    return Product.objects.create(
        creator=creator, type=product_type, title="굿즈", price=price
    )


def _paid_order(
    buyer: Account,
    product: Product,
    *,
    status: str = OrderStatus.PAID.value,
    qty: int = 1,
) -> Order:
    """Create an order (+ one line) for ``product`` in ``status`` (default PAID)."""
    order = Order.objects.create(
        buyer=buyer,
        status=status,
        subtotal=product.price * qty,
        total=product.price * qty,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        title=product.title,
        item_type=product.type,
        qty=qty,
        price=product.price,
    )
    return order


# --- happy path ------------------------------------------------------------- #


def test_paid_ship_complete_happy_path(client: Client) -> None:
    """PAID → ship (creator) → SHIPPING → complete → COMPLETED, with tracking stamped."""
    owner, creator = _owner_with_creator("stellar")
    order = _paid_order(_fan(), _product(creator))

    shipped = client.post(
        f"{BASE}/{order.id}/ship",
        data=json.dumps(SHIP_BODY),
        content_type=JSON,
        headers=_auth(owner),
    )
    assert shipped.status_code == 200
    body = shipped.json()
    assert body["status"] == "shipping"
    assert body["tracking"] == {"carrier": "CJ대한통운", "number": "1234567890"}
    order.refresh_from_db()
    assert order.status == OrderStatus.SHIPPING.value
    assert order.shipped_at is not None

    completed = client.post(
        f"{BASE}/{order.id}/complete", content_type=JSON, headers=_auth(owner)
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    order.refresh_from_db()
    assert order.status == OrderStatus.COMPLETED.value
    assert order.completed_at is not None


def test_operator_can_ship(client: Client) -> None:
    """An operator (not the owning creator) may also ship a PAID order."""
    _owner, creator = _owner_with_creator("stellar")
    order = _paid_order(_fan(), _product(creator))
    res = client.post(
        f"{BASE}/{order.id}/ship",
        data=json.dumps(SHIP_BODY),
        content_type=JSON,
        headers=_auth(_operator()),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "shipping"


# --- authorization ---------------------------------------------------------- #


def test_buyer_cannot_ship(client: Client) -> None:
    """The buyer (a fan) cannot self-transition their own order (leak-free 404/403)."""
    _owner, creator = _owner_with_creator("stellar")
    buyer = _fan()
    order = _paid_order(buyer, _product(creator))
    res = client.post(
        f"{BASE}/{order.id}/ship",
        data=json.dumps(SHIP_BODY),
        content_type=JSON,
        headers=_auth(buyer),
    )
    assert res.status_code in (403, 404)
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID.value  # untouched


def test_other_creator_cannot_ship(client: Client) -> None:
    """A different creator cannot ship an order for someone else's product (404)."""
    _owner, creator = _owner_with_creator("stellar")
    other_owner, _other = _owner_with_creator("nova")
    order = _paid_order(_fan(), _product(creator))
    res = client.post(
        f"{BASE}/{order.id}/ship",
        data=json.dumps(SHIP_BODY),
        content_type=JSON,
        headers=_auth(other_owner),
    )
    assert res.status_code in (403, 404)
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID.value  # untouched


def test_ship_requires_auth(client: Client) -> None:
    """An anonymous caller cannot ship (401/403)."""
    _owner, creator = _owner_with_creator("stellar")
    order = _paid_order(_fan(), _product(creator))
    res = client.post(
        f"{BASE}/{order.id}/ship", data=json.dumps(SHIP_BODY), content_type=JSON
    )
    assert res.status_code in (401, 403)


# --- illegal transitions ---------------------------------------------------- #


def test_ship_completed_order_is_422(client: Client) -> None:
    """Shipping an already-completed order is refused by the rowcount gate (422)."""
    owner, creator = _owner_with_creator("stellar")
    order = _paid_order(_fan(), _product(creator), status=OrderStatus.COMPLETED.value)
    res = client.post(
        f"{BASE}/{order.id}/ship",
        data=json.dumps(SHIP_BODY),
        content_type=JSON,
        headers=_auth(owner),
    )
    assert res.status_code == 422
    assert res.json()["code"] == "OrderNotShippable"


def test_ship_cancelled_order_is_422(client: Client) -> None:
    """Shipping a cancelled order is refused (422)."""
    owner, creator = _owner_with_creator("stellar")
    order = _paid_order(_fan(), _product(creator), status=OrderStatus.CANCELLED.value)
    res = client.post(
        f"{BASE}/{order.id}/ship",
        data=json.dumps(SHIP_BODY),
        content_type=JSON,
        headers=_auth(owner),
    )
    assert res.status_code == 422
    assert res.json()["code"] == "OrderNotShippable"


def test_complete_unshipped_goods_order_is_422(client: Client) -> None:
    """A physical (goods) order cannot be completed straight from PAID — it must ship."""
    owner, creator = _owner_with_creator("stellar")
    order = _paid_order(_fan(), _product(creator))
    res = client.post(
        f"{BASE}/{order.id}/complete", content_type=JSON, headers=_auth(owner)
    )
    assert res.status_code == 422
    assert res.json()["code"] == "OrderNotCompletable"
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID.value  # untouched


def test_complete_completed_order_is_422(client: Client) -> None:
    """Completing an already-completed order is refused (single-winner rowcount gate)."""
    owner, creator = _owner_with_creator("stellar")
    order = _paid_order(
        _fan(), _product(creator, product_type="digital"), status=OrderStatus.COMPLETED.value
    )
    res = client.post(
        f"{BASE}/{order.id}/complete", content_type=JSON, headers=_auth(owner)
    )
    assert res.status_code == 422
    assert res.json()["code"] == "OrderNotCompletable"


# --- digital delivery ------------------------------------------------------- #


def test_digital_order_completes_from_paid_without_shipping(client: Client) -> None:
    """A digital-only order is delivered by completing directly from PAID (no ship step)."""
    owner, creator = _owner_with_creator("stellar")
    order = _paid_order(_fan(), _product(creator, product_type="digital"))
    res = client.post(
        f"{BASE}/{order.id}/complete", content_type=JSON, headers=_auth(owner)
    )
    assert res.status_code == 200
    assert res.json()["status"] == "completed"
    order.refresh_from_db()
    assert order.status == OrderStatus.COMPLETED.value
    assert order.completed_at is not None
    assert order.shipped_at is None  # never shipped


# --- studio order queue ----------------------------------------------------- #


def test_studio_orders_lists_only_own_creator_orders(client: Client) -> None:
    """``/studio/orders`` returns the caller's creator's orders, never another's."""
    owner_a, creator_a = _owner_with_creator("stellar")
    _owner_b, creator_b = _owner_with_creator("nova")
    order_a = _paid_order(_fan(), _product(creator_a))
    order_b = _paid_order(_fan(), _product(creator_b))

    body = client.get(STUDIO_ORDERS, headers=_auth(owner_a)).json()
    assert "next_cursor" in body
    ids = {row["id"] for row in body["items"]}
    assert ids == {order_a.id}
    assert order_b.id not in ids


def test_studio_orders_requires_creator_403(client: Client) -> None:
    """A plain fan (operates no creator) is refused the studio order queue (403)."""
    res = client.get(STUDIO_ORDERS, headers=_auth(_fan()))
    assert res.status_code == 403
    assert res.json()["code"] == "OwnerRequired"


def test_studio_orders_requires_auth(client: Client) -> None:
    """An anonymous caller is refused the studio order queue (401/403)."""
    assert client.get(STUDIO_ORDERS).status_code in (401, 403)
