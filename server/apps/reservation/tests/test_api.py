"""Tests for the reservation API (F03, ASS-109 v0).

Covers the operator surface (create-on-behalf, daily list, confirm/change/
cancel/no-show), the fan surface (register/list/cancel own, bearer-only), and
the gates: operator role, fan role, ownership, blocked fan, and anonymous.
"""

from __future__ import annotations

import json
import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.reservation.models import Reservation
from apps.safety.models import BlockScope, UserBlock

pytestmark = pytest.mark.django_db

OP = "/api/operator/reservations"
FAN = "/api/fan/reservations"
JSON = "application/json"


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _tomorrow() -> str:
    """ISO date string for tomorrow (passes the past-date guard)."""
    return (timezone.localdate() + timedelta(days=1)).isoformat()


def test_operator_creates_and_lists(client: Client) -> None:
    """An operator records a reservation for a fan and sees it in the day's list."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    day = _tomorrow()
    created = client.post(
        OP,
        data=json.dumps(
            {
                "fan_id": str(fan.fan_id),
                "reserved_date": day,
                "reserved_time": "14:00",
                "party_size": 2,
            }
        ),
        content_type=JSON,
        headers=_auth(op),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["fan_id"] == str(fan.fan_id)
    assert body["status"] == "requested"

    listed = client.get(f"{OP}?date={day}", headers=_auth(op))
    assert listed.status_code == 200
    assert any(row["id"] == body["id"] for row in listed.json())


def test_operator_create_unknown_fan_is_404(client: Client) -> None:
    """Creating for a non-existent fan id is a 404."""
    op = _account(Role.OPERATOR.value)
    res = client.post(
        OP,
        data=json.dumps({"fan_id": str(uuid.uuid4()), "reserved_date": _tomorrow()}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 404


def test_operator_lifecycle_confirm_change_cancel(client: Client) -> None:
    """Operator drives a reservation through confirm → change → cancel."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    created = client.post(
        OP,
        data=json.dumps({"fan_id": str(fan.fan_id), "reserved_date": _tomorrow()}),
        content_type=JSON,
        headers=_auth(op),
    )
    rid = created.json()["id"]

    confirmed = client.post(f"{OP}/{rid}/confirm", content_type=JSON, headers=_auth(op))
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    changed = client.post(
        f"{OP}/{rid}/change",
        data=json.dumps({"party_size": 4}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert changed.status_code == 200
    assert changed.json()["party_size"] == 4

    cancelled = client.post(
        f"{OP}/{rid}/cancel",
        data=json.dumps({"reason": "store closed"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_operator_no_show(client: Client) -> None:
    """Operator marks a confirmed reservation as a no-show."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    created = client.post(
        OP,
        data=json.dumps({"fan_id": str(fan.fan_id), "reserved_date": _tomorrow()}),
        content_type=JSON,
        headers=_auth(op),
    )
    rid = created.json()["id"]
    client.post(f"{OP}/{rid}/confirm", content_type=JSON, headers=_auth(op))
    res = client.post(
        f"{OP}/{rid}/no-show",
        data=json.dumps({"reason": "did not arrive"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "no_show"


def test_fan_registers_and_lists_own(client: Client) -> None:
    """A fan registers a reservation over bearer auth and lists their own."""
    fan = _account(Role.FAN.value)
    created = client.post(
        FAN,
        data=json.dumps({"reserved_date": _tomorrow(), "party_size": 2}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "requested"
    assert "fan_id" not in body  # fan view omits operator-only fields

    listed = client.get(FAN, headers=_auth(fan))
    assert listed.status_code == 200
    assert any(row["id"] == body["id"] for row in listed.json())


def test_fan_cancels_own(client: Client) -> None:
    """A fan cancels their own reservation."""
    fan = _account(Role.FAN.value)
    created = client.post(
        FAN,
        data=json.dumps({"reserved_date": _tomorrow()}),
        content_type=JSON,
        headers=_auth(fan),
    )
    rid = created.json()["id"]
    res = client.post(f"{FAN}/{rid}/cancel", content_type=JSON, headers=_auth(fan))
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


def test_fan_cannot_cancel_another_fans_reservation(client: Client) -> None:
    """A fan cancelling someone else's reservation gets a 404 (no existence leak)."""
    owner = _account(Role.FAN.value)
    other = _account(Role.FAN.value)
    created = client.post(
        FAN,
        data=json.dumps({"reserved_date": _tomorrow()}),
        content_type=JSON,
        headers=_auth(owner),
    )
    rid = created.json()["id"]
    res = client.post(f"{FAN}/{rid}/cancel", content_type=JSON, headers=_auth(other))
    assert res.status_code == 404


def test_blocked_fan_is_refused(client: Client) -> None:
    """A blocked fan cannot register a reservation (ASS-111 enforcement)."""
    fan = _account(Role.FAN.value)
    UserBlock.objects.create(
        target=fan,
        block_scope=BlockScope.RESERVATION.value,
        block_reason="policy_violation",
        effective_from=timezone.now(),
        created_by=_account(Role.MANAGER.value),
    )
    res = client.post(
        FAN,
        data=json.dumps({"reserved_date": _tomorrow()}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 400


def test_staff_token_cannot_use_fan_endpoint(client: Client) -> None:
    """fan_auth is role-agnostic, so a staff token is refused on the fan surface (403)."""
    op = _account(Role.OPERATOR.value)
    res = client.post(
        FAN,
        data=json.dumps({"reserved_date": _tomorrow()}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 403


def test_fan_and_anonymous_refused_on_operator_endpoint(client: Client) -> None:
    """The operator surface rejects fan tokens and anonymous callers."""
    fan = _account(Role.FAN.value)
    assert client.get(OP, headers=_auth(fan)).status_code in {401, 403}
    assert client.get(OP).status_code in {401, 403}
    assert client.get(FAN).status_code in {401, 403}


def test_operator_list_filters_by_date(client: Client) -> None:
    """A reservation lists under its reserved date, not under today."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    day = _tomorrow()
    created = client.post(
        OP,
        data=json.dumps({"fan_id": str(fan.fan_id), "reserved_date": day}),
        content_type=JSON,
        headers=_auth(op),
    )
    rid = created.json()["id"]
    on_day = client.get(f"{OP}?date={day}", headers=_auth(op))
    assert any(r["id"] == rid for r in on_day.json())
    today = client.get(OP, headers=_auth(op))
    assert not any(r["id"] == rid for r in today.json())


def test_party_size_zero_is_422(client: Client) -> None:
    """Party size below 1 is rejected by schema validation (422)."""
    fan = _account(Role.FAN.value)
    res = client.post(
        FAN,
        data=json.dumps({"reserved_date": _tomorrow(), "party_size": 0}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 422


def test_fan_cancel_stores_no_fan_reason(client: Client) -> None:
    """The fan cancel endpoint accepts no reason, so no fan free-text is stored."""
    fan = _account(Role.FAN.value)
    created = client.post(
        FAN,
        data=json.dumps({"reserved_date": _tomorrow()}),
        content_type=JSON,
        headers=_auth(fan),
    )
    rid = created.json()["id"]
    # Even if a fan injects a reason in the body, the endpoint binds none of it.
    res = client.post(
        f"{FAN}/{rid}/cancel",
        data=json.dumps({"reason": "secret personal note"}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 200
    assert Reservation.objects.get(id=rid).cancellation_reason == ""


def test_fan_create_invalid_type_does_not_echo_input(client: Client) -> None:
    """An invalid reservation_type is rejected (400) without echoing the raw input."""
    fan = _account(Role.FAN.value)
    res = client.post(
        FAN,
        data=json.dumps({"reserved_date": _tomorrow(), "reservation_type": "INJECT-PII-123"}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 400
    assert "INJECT-PII-123" not in res.json()["detail"]
