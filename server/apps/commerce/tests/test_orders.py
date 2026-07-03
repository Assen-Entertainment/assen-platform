"""Tests for the commerce order flow (E11/B4 — mock orders, no money moves)."""

from __future__ import annotations

import json

import pytest
from django.test import Client

from apps.commerce.models import Order, OrderStatus, Product
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.notification.models import Notification

pytestmark = pytest.mark.django_db

BASE = "/api/orders"
JSON = "application/json"


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    """Return a test-client headers mapping bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _product(**kwargs: object) -> Product:
    """Create a product with sensible defaults."""
    defaults: dict[str, object] = {"type": "goods", "title": "굿즈", "price": 10000}
    defaults.update(kwargs)
    creator = Creator.objects.create(handle="stellar", name="별빛")
    defaults.setdefault("creator", creator)
    return Product.objects.create(**defaults)


def test_extended_product_fields_in_read_api(client: Client) -> None:
    """The product read API exposes the B4 extended fields."""
    _product(description="설명", options=["A", "B"], stock=5, sold_out=False, locked=True)
    row = client.get("/api/products").json()["items"][0]
    assert row["description"] == "설명"
    assert row["options"] == ["A", "B"]
    assert row["stock"] == 5
    assert row["sold_out"] is False
    assert row["locked"] is True


def test_create_order_snapshots_and_notifies(client: Client) -> None:
    """Placing an order records a paid order, snapshots the line, and notifies."""
    fan = _fan()
    product = _product(title="아크릴 스탠드", price=18000)
    res = client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id), "qty": 2, "option": "A타입"}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "paid"
    assert body["id"].startswith("ASN-")
    assert body["total"] == 36000
    assert body["items"][0]["title"] == "아크릴 스탠드"
    assert body["items"][0]["qty"] == 2
    assert body["items"][0]["option"] == "A타입"
    assert body["creator_name"] == "별빛"
    # Exactly one order notification is self-wired on creation.
    notifs = Notification.objects.filter(recipient=fan, kind="order")
    assert notifs.count() == 1


def test_create_order_is_idempotent_by_key(client: Client) -> None:
    """A retried order with the same idempotency key returns the original (B1)."""
    fan = _fan()
    product = _product(price=10000)
    body = {"product_id": str(product.id), "qty": 1, "idempotency_key": "order-key-1"}

    first = client.post(BASE, data=json.dumps(body), content_type=JSON, headers=_auth(fan))
    assert first.status_code == 201
    order_id = first.json()["id"]

    # Same key again → the existing order (200), no duplicate row.
    again = client.post(BASE, data=json.dumps(body), content_type=JSON, headers=_auth(fan))
    assert again.status_code == 200
    assert again.json()["id"] == order_id
    assert Order.objects.filter(buyer=fan).count() == 1


def test_create_order_sold_out_is_422(client: Client) -> None:
    """A sold-out product cannot be ordered."""
    fan = _fan()
    product = _product(sold_out=True)
    res = client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 422
    assert "detail" in res.json()


def test_create_order_insufficient_stock_is_422(client: Client) -> None:
    """Ordering more than the tracked stock is refused."""
    fan = _fan()
    product = _product(stock=1)
    res = client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id), "qty": 3}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 422


def test_create_order_locked_is_422(client: Client) -> None:
    """A membership-locked product cannot be ordered directly."""
    fan = _fan()
    product = _product(locked=True)
    res = client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 422


def test_cancel_transitions_and_guard(client: Client) -> None:
    """A paid order cancels; a completed order cannot be cancelled (422)."""
    fan = _fan()
    product = _product()
    created = client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    order_id = created.json()["id"]
    res = client.post(f"{BASE}/{order_id}/cancel", content_type=JSON, headers=_auth(fan))
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"

    # A completed order is not cancellable.
    order = Order.objects.get(id=order_id)
    order.status = OrderStatus.COMPLETED.value
    order.save(update_fields=["status"])
    again = client.post(f"{BASE}/{order_id}/cancel", content_type=JSON, headers=_auth(fan))
    assert again.status_code == 422


def test_refund_request_flow(client: Client) -> None:
    """A shipping order accepts a refund request; a second one is refused (422)."""
    fan = _fan()
    product = _product()
    order_id = client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(fan),
    ).json()["id"]
    order = Order.objects.get(id=order_id)
    order.status = OrderStatus.SHIPPING.value
    order.save(update_fields=["status"])

    res = client.post(
        f"{BASE}/{order_id}/refund",
        data=json.dumps({"reason": "단순 변심", "detail": "사이즈 문제"}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 200
    assert res.json()["refund"]["status"] == "requested"
    assert res.json()["refund"]["reason"] == "단순 변심"

    dup = client.post(
        f"{BASE}/{order_id}/refund",
        data=json.dumps({"reason": "다시"}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert dup.status_code == 422


def test_refund_on_paid_order_is_422(client: Client) -> None:
    """A paid (not yet shipping/completed) order cannot be refunded."""
    fan = _fan()
    product = _product()
    order_id = client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(fan),
    ).json()["id"]
    res = client.post(
        f"{BASE}/{order_id}/refund",
        data=json.dumps({"reason": "x"}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 422


def test_list_returns_only_own_orders(client: Client) -> None:
    """The order list is scoped to the requesting fan (cursor page shape)."""
    owner = _fan()
    other = _fan()
    product = _product()
    client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(owner),
    )
    listed = client.get(BASE, headers=_auth(owner)).json()
    assert len(listed["items"]) == 1
    assert "next_cursor" in listed
    assert client.get(BASE, headers=_auth(other)).json()["items"] == []


def test_get_another_fans_order_is_404(client: Client) -> None:
    """Reading someone else's order is a 404 (no existence leak)."""
    owner = _fan()
    other = _fan()
    product = _product()
    order_id = client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(owner),
    ).json()["id"]
    res = client.get(f"{BASE}/{order_id}", headers=_auth(other))
    assert res.status_code == 404


def test_create_order_requires_auth(client: Client) -> None:
    """An anonymous caller cannot place an order."""
    product = _product()
    res = client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
    )
    assert res.status_code == 401


def test_open_refund_unique_constraint_blocks_concurrent_duplicate() -> None:
    """열린 환불 1건 불변식이 DB 제약으로 봉인된다(check-then-create 경합의 패자)."""
    from django.db import IntegrityError, transaction

    from apps.commerce.models import RefundRequest, RefundStatus

    order = Order.objects.create(
        buyer=_fan(), status=OrderStatus.COMPLETED.value, total=1000
    )
    RefundRequest.objects.create(order=order, reason="사유", status=RefundStatus.REQUESTED)
    with pytest.raises(IntegrityError), transaction.atomic():
        RefundRequest.objects.create(order=order, reason="중복", status=RefundStatus.REQUESTED)

    # 종결 상태(rejected)로 바뀌면 새 신청은 다시 허용된다(조건부 제약).
    RefundRequest.objects.filter(order=order).update(status=RefundStatus.REJECTED)
    RefundRequest.objects.create(order=order, reason="재신청", status=RefundStatus.REQUESTED)
