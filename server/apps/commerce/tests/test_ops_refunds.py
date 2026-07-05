"""Tests for the operator refund review flow (R6-W1A — mock orders, no money moves).

Covers the load-bearing rules: the routes are operator-gated (a fan is refused),
each transition is a single-winner rowcount gate (no double accept/reject), accept
cancels + restocks the owning order exactly once (and never double-restocks when a
fan already cancelled it), reject demands a reason, and every transition leaves an
audit entry and notifies the fan.
"""

from __future__ import annotations

import json
import uuid

import pytest
from django.test import Client

from apps.audit.models import AuditAction, AuditEntry
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
from apps.notification.models import Notification

pytestmark = pytest.mark.django_db

BASE = "/api/ops/refunds"
JSON = "application/json"


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def _operator() -> Account:
    """Create an operator account (no username — token auth carries the account)."""
    return Account.objects.create(role=Role.OPERATOR.value)


def _auth(account: Account) -> dict[str, str]:
    """Return a test-client headers mapping bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _product(*, stock: int | None = None, sold_out: bool = False, price: int = 10000) -> Product:
    """Create a goods product owned by a fresh creator."""
    creator = Creator.objects.create(handle=f"c{uuid.uuid4().hex[:8]}", name="크리에이터")
    return Product.objects.create(
        type="goods", title="굿즈", price=price, creator=creator, stock=stock, sold_out=sold_out
    )


def _order_with_open_refund(
    *,
    buyer: Account,
    product: Product,
    qty: int = 1,
    order_status: str = OrderStatus.SHIPPING.value,
    refund_status: str = RefundStatus.REQUESTED.value,
) -> tuple[Order, RefundRequest]:
    """Create an order (+ one line) in ``order_status`` with a refund in ``refund_status``."""
    order = Order.objects.create(
        buyer=buyer, status=order_status, subtotal=product.price * qty, total=product.price * qty
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        title=product.title,
        item_type=product.type,
        qty=qty,
        price=product.price,
    )
    refund = RefundRequest.objects.create(order=order, reason="단순 변심", status=refund_status)
    return order, refund


# --- RBAC ------------------------------------------------------------------- #


def test_list_is_operator_gated(client: Client) -> None:
    """A fan token and an anonymous caller are both refused the operator queue."""
    assert client.get(BASE, headers=_auth(_fan())).status_code in (401, 403)
    assert client.get(BASE).status_code in (401, 403)


def test_accept_is_operator_gated(client: Client) -> None:
    """A fan cannot drive a refund transition (accept is operator+)."""
    fan = _fan()
    _, refund = _order_with_open_refund(buyer=fan, product=_product())
    res = client.post(f"{BASE}/{refund.id}/accept", content_type=JSON, headers=_auth(fan))
    assert res.status_code in (401, 403)
    refund.refresh_from_db()
    assert refund.status == RefundStatus.REQUESTED.value  # untouched


# --- list ------------------------------------------------------------------- #


def test_list_returns_only_open_refunds(client: Client) -> None:
    """The queue shows requested/reviewing only, not resolved ones, with a page shape."""
    fan = _fan()
    for status in (
        RefundStatus.REQUESTED.value,
        RefundStatus.REVIEWING.value,
        RefundStatus.ACCEPTED.value,
        RefundStatus.REJECTED.value,
    ):
        _order_with_open_refund(buyer=fan, product=_product(), refund_status=status)

    body = client.get(BASE, headers=_auth(_operator())).json()
    assert "next_cursor" in body
    statuses = {row["status"] for row in body["items"]}
    assert statuses == {"requested", "reviewing"}
    assert len(body["items"]) == 2
    row = body["items"][0]
    assert {"id", "order_id", "buyer_fan_id", "order_status", "order_total"}.issubset(row)


# --- review ----------------------------------------------------------------- #


def test_review_transitions_and_is_single_winner(client: Client) -> None:
    """requested→reviewing succeeds once; a second review is refused (422)."""
    op = _operator()
    _, refund = _order_with_open_refund(buyer=_fan(), product=_product())
    first = client.post(f"{BASE}/{refund.id}/review", content_type=JSON, headers=_auth(op))
    assert first.status_code == 200
    assert first.json()["status"] == "reviewing"
    refund.refresh_from_db()
    assert refund.status == RefundStatus.REVIEWING.value
    assert AuditEntry.objects.filter(
        action=AuditAction.REFUND_REVIEWED.value, target=str(refund.id)
    ).exists()

    second = client.post(f"{BASE}/{refund.id}/review", content_type=JSON, headers=_auth(op))
    assert second.status_code == 422
    assert second.json()["code"] == "RefundNotTransitionable"


def test_review_unknown_refund_is_404(client: Client) -> None:
    """Reviewing an unknown refund id is a 404."""
    unknown = uuid.uuid4()
    res = client.post(f"{BASE}/{unknown}/review", content_type=JSON, headers=_auth(_operator()))
    assert res.status_code == 404
    assert res.json()["code"] == "RefundNotFound"


# --- accept ----------------------------------------------------------------- #


def test_accept_cancels_order_restocks_and_notifies(client: Client) -> None:
    """Accept resolves the refund, cancels the order, restores stock, notifies the fan."""
    op = _operator()
    fan = _fan()
    product = _product(stock=5)
    order, refund = _order_with_open_refund(buyer=fan, product=product, qty=2)

    res = client.post(f"{BASE}/{refund.id}/accept", content_type=JSON, headers=_auth(op))
    assert res.status_code == 200
    assert res.json()["status"] == "accepted"
    assert res.json()["order_status"] == "cancelled"

    refund.refresh_from_db()
    order.refresh_from_db()
    product.refresh_from_db()
    assert refund.status == RefundStatus.ACCEPTED.value
    assert order.status == OrderStatus.CANCELLED.value
    assert product.stock == 7  # 5 + restored qty 2
    assert AuditEntry.objects.filter(
        action=AuditAction.REFUND_ACCEPTED.value, target=str(refund.id), actor=op
    ).exists()
    notif = Notification.objects.filter(recipient=fan, kind="order").first()
    assert notif is not None and "승인" in notif.title


def test_accept_reopens_auto_sold_out_product(client: Client) -> None:
    """Accepting restores stock and clears an auto sold-out (stock had hit 0)."""
    product = _product(stock=0, sold_out=True)
    _, refund = _order_with_open_refund(buyer=_fan(), product=product, qty=2)
    res = client.post(f"{BASE}/{refund.id}/accept", content_type=JSON, headers=_auth(_operator()))
    assert res.status_code == 200
    product.refresh_from_db()
    assert product.stock == 2
    assert product.sold_out is False


def test_double_accept_is_422_and_restocks_once(client: Client) -> None:
    """A second accept is refused and never double-restores stock (rowcount seal)."""
    op = _operator()
    product = _product(stock=1)
    _, refund = _order_with_open_refund(buyer=_fan(), product=product, qty=1)

    first = client.post(f"{BASE}/{refund.id}/accept", content_type=JSON, headers=_auth(op))
    assert first.status_code == 200
    product.refresh_from_db()
    assert product.stock == 2  # 1 + 1

    second = client.post(f"{BASE}/{refund.id}/accept", content_type=JSON, headers=_auth(op))
    assert second.status_code == 422
    assert second.json()["code"] == "RefundNotTransitionable"
    product.refresh_from_db()
    assert product.stock == 2  # not inflated to 3


def test_accept_on_already_cancelled_order_skips_restock(client: Client) -> None:
    """A refund accepted on an order a fan already cancelled does not double-restore.

    The order-side rowcount gate only restocks when the order is still refundable; a
    cancelled order was restocked at cancel time, so accept resolves the refund but
    leaves stock alone.
    """
    product = _product(stock=5)
    _, refund = _order_with_open_refund(
        buyer=_fan(), product=product, qty=2, order_status=OrderStatus.CANCELLED.value
    )
    res = client.post(f"{BASE}/{refund.id}/accept", content_type=JSON, headers=_auth(_operator()))
    assert res.status_code == 200
    refund.refresh_from_db()
    product.refresh_from_db()
    assert refund.status == RefundStatus.ACCEPTED.value  # refund still resolved
    assert product.stock == 5  # NOT restocked again


# --- reject ----------------------------------------------------------------- #


def test_reject_requires_reason_and_transitions(client: Client) -> None:
    """Reject moves the refund to rejected, records the reason, and notifies the fan."""
    op = _operator()
    fan = _fan()
    _, refund = _order_with_open_refund(buyer=fan, product=_product())
    res = client.post(
        f"{BASE}/{refund.id}/reject",
        data=json.dumps({"reason": "증빙 불충분"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"
    refund.refresh_from_db()
    assert refund.status == RefundStatus.REJECTED.value
    assert AuditEntry.objects.filter(
        action=AuditAction.REFUND_REJECTED.value, target=str(refund.id), reason="증빙 불충분"
    ).exists()
    notif = Notification.objects.filter(recipient=fan, kind="order").first()
    assert notif is not None and "거절" in notif.title


def test_reject_without_reason_is_422(client: Client) -> None:
    """An empty reason fails schema validation (a rejection must state why)."""
    _, refund = _order_with_open_refund(buyer=_fan(), product=_product())
    res = client.post(
        f"{BASE}/{refund.id}/reject",
        data=json.dumps({"reason": ""}),
        content_type=JSON,
        headers=_auth(_operator()),
    )
    assert res.status_code == 422


def test_reject_after_accept_is_422(client: Client) -> None:
    """A resolved (accepted) refund can no longer be rejected — single-winner."""
    op = _operator()
    _, refund = _order_with_open_refund(buyer=_fan(), product=_product(stock=3))
    accepted = client.post(f"{BASE}/{refund.id}/accept", content_type=JSON, headers=_auth(op))
    assert accepted.status_code == 200
    res = client.post(
        f"{BASE}/{refund.id}/reject",
        data=json.dumps({"reason": "늦음"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 422
    assert res.json()["code"] == "RefundNotTransitionable"
