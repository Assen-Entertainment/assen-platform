"""Tests for the notification operator API (ASS-113 v0).

Covers the policy registry endpoint, dispatch of an allowed category (200), the
fail-closed refusals (forbidden/unknown category, real-time presence field,
cast-schedule date rule → 422), and the operator gate (fan/anon → 401/403).
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

POLICY = "/api/operator/notifications/policy"
DISPATCH = "/api/operator/notifications/dispatch"
JSON = "application/json"


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _dispatch(client: Client, op: Account, **over: object) -> Any:
    """POST a dispatch payload (with sane defaults) and return the response."""
    data: dict[str, object] = {
        "category": "reservation_status",
        "token": "device-1",
        "title": "예약 확정",
        "body": "예약이 확정되었습니다.",
    }
    data.update(over)
    return client.post(DISPATCH, data=json.dumps(data), content_type=JSON, headers=_auth(op))


def test_policy_lists_allowed_four_and_forbidden(client: Client) -> None:
    """The policy registry returns the four allowed categories and forbidden kinds."""
    op = _account(Role.OPERATOR.value)
    res = client.get(POLICY, headers=_auth(op))
    assert res.status_code == 200
    body = res.json()
    allowed = {c["value"] for c in body["allowed"]}
    assert allowed == {
        "reservation_status",
        "event_notice",
        "coupon",
        "favorite_cast_schedule",
    }
    forbidden = {f["value"] for f in body["forbidden"]}
    assert "high_value_payment_inducement" in forbidden
    assert all(c["label"] for c in body["allowed"])


def test_dispatch_allowed_category_is_accepted(client: Client) -> None:
    """An allowed category dispatches (200) and reports accepted."""
    op = _account(Role.OPERATOR.value)
    res = _dispatch(client, op)
    assert res.status_code == 200
    body = res.json()
    assert body["accepted"] is True
    assert body["category"] == "reservation_status"
    assert body["message_id"]


def test_dispatch_forbidden_category_is_422(client: Client) -> None:
    """A named-forbidden category is refused (422), not sent."""
    op = _account(Role.OPERATOR.value)
    res = _dispatch(client, op, category="high_value_payment_inducement")
    assert res.status_code == 422


def test_dispatch_unknown_category_is_422(client: Client) -> None:
    """An unlisted category is refused fail-closed (422)."""
    op = _account(Role.OPERATOR.value)
    res = _dispatch(client, op, category="surprise_promo")
    assert res.status_code == 422


def test_dispatch_realtime_presence_field_is_422(client: Client) -> None:
    """A real-time presence field in data is refused (422), any category."""
    op = _account(Role.OPERATOR.value)
    res = _dispatch(client, op, category="event_notice", data={"in_store_now": "true"})
    assert res.status_code == 422


def test_dispatch_cast_schedule_requires_future_date(client: Client) -> None:
    """A favourite-cast schedule needs a future date: future 200, past/missing 422."""
    op = _account(Role.OPERATOR.value)
    future = (timezone.localdate() + timedelta(days=4)).isoformat()
    ok = _dispatch(
        client,
        op,
        category="favorite_cast_schedule",
        title="예정 출근",
        body="요약",
        scheduled_date=future,
    )
    assert ok.status_code == 200

    missing = _dispatch(client, op, category="favorite_cast_schedule")
    assert missing.status_code == 422

    past = _dispatch(
        client,
        op,
        category="favorite_cast_schedule",
        scheduled_date=(timezone.localdate() - timedelta(days=1)).isoformat(),
    )
    assert past.status_code == 422

    today = _dispatch(
        client,
        op,
        category="favorite_cast_schedule",
        scheduled_date=timezone.localdate().isoformat(),
    )
    assert today.status_code == 422


def test_dispatch_reserved_data_key_is_422(client: Client) -> None:
    """A caller cannot override the stamped scheduled_date/category via data."""
    op = _account(Role.OPERATOR.value)
    future = (timezone.localdate() + timedelta(days=4)).isoformat()
    res = _dispatch(
        client,
        op,
        category="favorite_cast_schedule",
        scheduled_date=future,
        data={"scheduled_date": "2020-01-01"},
    )
    assert res.status_code == 422


def test_dispatch_cased_realtime_key_is_422(client: Client) -> None:
    """A cased real-time presence key is still refused at the API layer."""
    op = _account(Role.OPERATOR.value)
    res = _dispatch(client, op, category="event_notice", data={"In_Store_Now": "true"})
    assert res.status_code == 422


def test_dispatch_too_many_data_keys_is_422(client: Client) -> None:
    """A data map over the key-count cap is refused (422)."""
    op = _account(Role.OPERATOR.value)
    res = _dispatch(client, op, data={str(i): "v" for i in range(21)})
    assert res.status_code == 422


def test_dispatch_oversized_data_value_is_422(client: Client) -> None:
    """A data value over the length cap is refused (422)."""
    op = _account(Role.OPERATOR.value)
    res = _dispatch(client, op, data={"k": "x" * 501})
    assert res.status_code == 422


def test_dispatch_empty_token_is_422(client: Client) -> None:
    """An empty device token fails request validation (422)."""
    op = _account(Role.OPERATOR.value)
    res = _dispatch(client, op, token="")
    assert res.status_code == 422


def test_operator_surface_refuses_fan_and_anonymous(client: Client) -> None:
    """The notification surface rejects fan tokens and anonymous callers."""
    fan = _account(Role.FAN.value)
    assert client.get(POLICY, headers=_auth(fan)).status_code in {401, 403}
    assert client.get(POLICY).status_code in {401, 403}
    assert _dispatch(client, fan).status_code in {401, 403}
