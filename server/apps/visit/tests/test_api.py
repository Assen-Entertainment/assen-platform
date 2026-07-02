"""Acceptance tests for the operator visit API."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.visit.models import VisitRecordStatus
from apps.visit.services import record_visit, void_visit

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token.

    Uses the ``headers=`` request kwarg (Django 4.2+) rather than ``**extra``
    HTTP_ kwargs so the call type-checks cleanly under django-stubs strict mode.
    """
    token = issue_token_pair(account).access_token
    return {"authorization": f"Bearer {token}"}


def test_create_and_list_visits(client: Client) -> None:
    """An operator can create a manual check-in and list the same business day."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    visited_at = timezone.now()

    response = client.post(
        "/api/operator/visits/",
        data={
            "fan_id": str(fan.fan_id),
            "visited_at": visited_at.isoformat(),
            "note": "manual desk check-in",
        },
        content_type="application/json",
        headers=_auth(operator),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["fan_id"] == str(fan.fan_id)
    assert body["status"] == VisitRecordStatus.ACTIVE.value

    list_response = client.get(
        "/api/operator/visits/",
        data={"date": timezone.localdate(visited_at).isoformat()},
        headers=_auth(operator),
    )
    assert list_response.status_code == 200
    rows = list_response.json()
    assert [row["id"] for row in rows] == [body["id"]]


def test_patch_visit(client: Client) -> None:
    """An operator can correct timestamp and note fields."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    record = record_visit(fan=fan, visited_at=timezone.now(), actor=operator)
    corrected_at = record.visited_at + timedelta(minutes=3)

    response = client.patch(
        f"/api/operator/visits/{record.id}",
        data={"visited_at": corrected_at.isoformat(), "note": "fixed time"},
        content_type="application/json",
        headers=_auth(operator),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["note"] == "fixed time"
    assert body["id"] == str(record.id)


def test_void_visit_and_revoid_rejected(client: Client) -> None:
    """Voiding requires a reason and a second void returns 400."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    record = record_visit(fan=fan, visited_at=timezone.now(), actor=operator)
    headers = _auth(operator)

    response = client.post(
        f"/api/operator/visits/{record.id}/void",
        data={"reason": "entered twice"},
        content_type="application/json",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == VisitRecordStatus.VOIDED.value

    again = client.post(
        f"/api/operator/visits/{record.id}/void",
        data={"reason": "again"},
        content_type="application/json",
        headers=headers,
    )
    assert again.status_code == 400


def test_permission_denied_for_fan_token(client: Client) -> None:
    """A valid non-staff token cannot access operator visit routes."""
    fan = _account(Role.FAN.value)

    response = client.get("/api/operator/visits/", headers=_auth(fan))

    assert response.status_code in {401, 403}


def test_missing_fan_and_record_return_404(client: Client) -> None:
    """Unknown fan UUIDs and visit UUIDs return 404."""
    operator = _account(Role.OPERATOR.value)
    headers = _auth(operator)
    missing_id = "00000000-0000-0000-0000-000000000000"

    create_response = client.post(
        "/api/operator/visits/",
        data={"fan_id": missing_id},
        content_type="application/json",
        headers=headers,
    )
    assert create_response.status_code == 404

    patch_response = client.patch(
        f"/api/operator/visits/{missing_id}",
        data={"note": "missing"},
        content_type="application/json",
        headers=headers,
    )
    assert patch_response.status_code == 404


def test_voided_records_are_listed(client: Client) -> None:
    """The date list includes voided records with status exposed."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    record = record_visit(fan=fan, visited_at=timezone.now(), actor=operator)
    void_visit(record=record, reason="bad scan", actor=operator)

    response = client.get("/api/operator/visits/", headers=_auth(operator))

    assert response.status_code == 200
    rows = response.json()
    assert rows[0]["status"] == VisitRecordStatus.VOIDED.value
