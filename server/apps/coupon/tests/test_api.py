"""Tests for the coupon + point API (F09, ASS-108 v0).

Covers the operator surface (issue/list/redeem/cancel/expire, point grant/adjust/
read) and the fan surface (own coupons + point balance), plus the gates (operator
role, fan role, blocked-fan redeem refusal).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.safety.models import BlockScope, UserBlock

pytestmark = pytest.mark.django_db

OP = "/api/operator/coupon"
FAN = "/api/fan/coupon"
JSON = "application/json"


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _issue(client: Client, op: Account, fan: Account, **over: object) -> Any:
    """Issue a coupon via the operator API and return the body."""
    data: dict[str, object] = {"fan_id": str(fan.fan_id), "coupon_type": "revisit"}
    data.update(over)
    res = client.post(f"{OP}/coupons", data=json.dumps(data), content_type=JSON, headers=_auth(op))
    assert res.status_code == 201, res.content
    return res.json()


def test_operator_issues_lists_and_redeems(client: Client) -> None:
    """An operator issues a coupon, lists it, and redeems it."""
    op, fan = _account(Role.OPERATOR.value), _account(Role.FAN.value)
    body = _issue(client, op, fan)
    assert body["status"] == "active"
    assert body["redemption_id"] is None

    listed = client.get(f"{OP}/coupons?fan_id={fan.fan_id}", headers=_auth(op))
    assert listed.status_code == 200
    assert any(c["id"] == body["id"] for c in listed.json())

    red = client.post(f"{OP}/coupons/{body['id']}/redeem", content_type=JSON, headers=_auth(op))
    assert red.status_code == 200
    redeemed = red.json()
    assert redeemed["status"] == "redeemed"
    assert redeemed["redemption_id"] is not None


def test_operator_cancel_and_expire(client: Client) -> None:
    """An operator cancels one coupon and expires another."""
    op, fan = _account(Role.OPERATOR.value), _account(Role.FAN.value)
    c1 = _issue(client, op, fan)["id"]
    c2 = _issue(client, op, fan)["id"]
    cancelled = client.post(f"{OP}/coupons/{c1}/cancel", content_type=JSON, headers=_auth(op))
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    expired = client.post(f"{OP}/coupons/{c2}/expire", content_type=JSON, headers=_auth(op))
    assert expired.status_code == 200
    assert expired.json()["status"] == "expired"


def test_blocked_fan_redeem_is_400(client: Client) -> None:
    """A blocked fan's coupon cannot be redeemed (400)."""
    op, fan = _account(Role.OPERATOR.value), _account(Role.FAN.value)
    UserBlock.objects.create(
        target=fan,
        block_scope=BlockScope.FANDOM_FEATURE.value,
        block_reason="policy_violation",
        effective_from=timezone.now(),
        created_by=_account(Role.MANAGER.value),
    )
    cid = _issue(client, op, fan)["id"]
    res = client.post(f"{OP}/coupons/{cid}/redeem", content_type=JSON, headers=_auth(op))
    assert res.status_code == 400


def test_operator_grants_adjusts_and_reads_points(client: Client) -> None:
    """An operator grants then adjusts points and reads the balance."""
    op, fan = _account(Role.OPERATOR.value), _account(Role.FAN.value)
    grant = client.post(
        f"{OP}/points/grant",
        data=json.dumps({"fan_id": str(fan.fan_id), "delta": 50, "reason": "welcome"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert grant.status_code == 200
    assert grant.json()["delta"] == 50
    adj = client.post(
        f"{OP}/points/adjust",
        data=json.dumps({"fan_id": str(fan.fan_id), "delta": -20}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert adj.status_code == 200
    bal = client.get(f"{OP}/points/{fan.fan_id}", headers=_auth(op))
    assert bal.status_code == 200
    assert bal.json()["balance"] == 30


def test_negative_balance_adjust_is_400(client: Client) -> None:
    """An adjustment that would underflow the balance is refused (400)."""
    op, fan = _account(Role.OPERATOR.value), _account(Role.FAN.value)
    res = client.post(
        f"{OP}/points/adjust",
        data=json.dumps({"fan_id": str(fan.fan_id), "delta": -5}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 400


def test_fan_sees_own_coupons_and_points(client: Client) -> None:
    """A fan reads their own coupons and point balance."""
    op, fan = _account(Role.OPERATOR.value), _account(Role.FAN.value)
    _issue(client, op, fan)
    client.post(
        f"{OP}/points/grant",
        data=json.dumps({"fan_id": str(fan.fan_id), "delta": 15}),
        content_type=JSON,
        headers=_auth(op),
    )
    coupons = client.get(f"{FAN}/coupons", headers=_auth(fan))
    assert coupons.status_code == 200
    assert len(coupons.json()) == 1
    points = client.get(f"{FAN}/points", headers=_auth(fan))
    assert points.status_code == 200
    assert points.json()["balance"] == 15


def test_fan_does_not_see_other_fans_coupons(client: Client) -> None:
    """The fan coupon list is scoped to the requesting fan."""
    op = _account(Role.OPERATOR.value)
    owner, other = _account(Role.FAN.value), _account(Role.FAN.value)
    _issue(client, op, owner)
    assert client.get(f"{FAN}/coupons", headers=_auth(other)).json() == []


def test_fan_does_not_see_other_fans_points(client: Client) -> None:
    """The fan point balance/ledger is scoped to the requesting fan."""
    op = _account(Role.OPERATOR.value)
    owner, other = _account(Role.FAN.value), _account(Role.FAN.value)
    client.post(
        f"{OP}/points/grant",
        data=json.dumps({"fan_id": str(owner.fan_id), "delta": 25}),
        content_type=JSON,
        headers=_auth(op),
    )
    res = client.get(f"{FAN}/points", headers=_auth(other))
    assert res.status_code == 200
    body = res.json()
    assert body["balance"] == 0
    assert body["entries"] == []


def test_fan_points_omit_operator_reason(client: Client) -> None:
    """The fan point ledger never exposes the operator-only reason note."""
    op, fan = _account(Role.OPERATOR.value), _account(Role.FAN.value)
    client.post(
        f"{OP}/points/grant",
        data=json.dumps({"fan_id": str(fan.fan_id), "delta": 10, "reason": "internal note"}),
        content_type=JSON,
        headers=_auth(op),
    )
    body = client.get(f"{FAN}/points", headers=_auth(fan)).json()
    assert body["balance"] == 10
    assert body["entries"]
    assert all("reason" not in entry for entry in body["entries"])


def test_grant_is_idempotent_via_reference(client: Client) -> None:
    """A retried grant with the same reference does not double the balance."""
    op, fan = _account(Role.OPERATOR.value), _account(Role.FAN.value)
    body = json.dumps({"fan_id": str(fan.fan_id), "delta": 20, "reference": "visit-7"})
    first = client.post(f"{OP}/points/grant", data=body, content_type=JSON, headers=_auth(op))
    again = client.post(f"{OP}/points/grant", data=body, content_type=JSON, headers=_auth(op))
    assert first.status_code == 200
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]
    bal = client.get(f"{OP}/points/{fan.fan_id}", headers=_auth(op))
    assert bal.json()["balance"] == 20


def test_staff_token_refused_on_fan_surface(client: Client) -> None:
    """fan_auth is role-agnostic, so a staff token is refused on the fan reads (403)."""
    op = _account(Role.OPERATOR.value)
    assert client.get(f"{FAN}/coupons", headers=_auth(op)).status_code == 403
    assert client.get(f"{FAN}/points", headers=_auth(op)).status_code == 403


def test_operator_surface_refuses_fan_and_anonymous(client: Client) -> None:
    """The operator surface rejects fan tokens and anonymous callers."""
    fan = _account(Role.FAN.value)
    assert client.get(f"{OP}/coupons", headers=_auth(fan)).status_code in {401, 403}
    assert client.get(f"{OP}/coupons").status_code in {401, 403}
    assert client.get(f"{FAN}/coupons").status_code in {401, 403}
