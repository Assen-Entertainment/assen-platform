"""Acceptance tests for the rotating QR check-in API (ASS-99)."""

from __future__ import annotations

import pytest
from django.test import Client

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.visit.checkin_services import issue_checkin_token
from apps.visit.models import VisitRecord, VisitRecordSource

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    token = issue_token_pair(account).access_token
    return {"authorization": f"Bearer {token}"}


def test_fan_issues_checkin_token(client: Client) -> None:
    """A fan gets a short-lived rotating token to render as a QR."""
    fan = _account(Role.FAN.value)
    response = client.post("/api/checkin/token", headers=_auth(fan))
    assert response.status_code == 201
    body = response.json()
    assert body["token"]
    assert body["ttl_seconds"] > 0
    assert "expires_at" in body


def test_non_fan_cannot_issue_token(client: Client) -> None:
    """An operator account cannot request a fan check-in QR (403)."""
    operator = _account(Role.OPERATOR.value)
    response = client.post("/api/checkin/token", headers=_auth(operator))
    assert response.status_code == 403


def test_unauthenticated_issue_is_rejected(client: Client) -> None:
    """No bearer token → 401."""
    response = client.post("/api/checkin/token")
    assert response.status_code == 401


def test_operator_redeems_token_into_visit(client: Client) -> None:
    """An operator redeems a scanned token; a QR visit is recorded."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    _token, raw = issue_checkin_token(fan=fan)

    response = client.post(
        "/api/operator/checkin/redeem",
        data={"token": raw},
        content_type="application/json",
        headers=_auth(operator),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fan_id"] == str(fan.fan_id)
    assert body["checkin_method"] == "qr"
    record = VisitRecord.objects.get(id=body["visit_id"])
    assert record.source == VisitRecordSource.QR_SELF.value


def test_redeem_invalid_token_returns_400(client: Client) -> None:
    """An unknown/expired token redeem returns 400, not 500."""
    operator = _account(Role.OPERATOR.value)
    response = client.post(
        "/api/operator/checkin/redeem",
        data={"token": "definitely-not-valid"},
        content_type="application/json",
        headers=_auth(operator),
    )
    assert response.status_code == 400
    assert VisitRecord.objects.count() == 0


def test_fan_cannot_redeem(client: Client) -> None:
    """The redeem endpoint is operator-gated; a fan token is denied."""
    fan = _account(Role.FAN.value)
    other_fan = _account(Role.FAN.value)
    _token, raw = issue_checkin_token(fan=other_fan)
    response = client.post(
        "/api/operator/checkin/redeem",
        data={"token": raw},
        content_type="application/json",
        headers=_auth(fan),
    )
    assert response.status_code in {401, 403}
    assert VisitRecord.objects.count() == 0
