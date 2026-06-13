"""Acceptance tests for the operator cheki API."""

from __future__ import annotations

import pytest
from django.test import Client
from django.utils import timezone

from apps.cheki.models import ChekiRecordStatus
from apps.cheki.services import record_cheki, void_cheki
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.visit.models import VisitRecord

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _visit(operator: Account) -> VisitRecord:
    """Create a bare visit row for cheki tests."""
    return VisitRecord.objects.create(
        fan=_account(Role.FAN.value),
        visited_at=timezone.now(),
        created_by=operator,
    )


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    token = issue_token_pair(account).access_token
    return {"authorization": f"Bearer {token}"}


def test_create_and_list_cheki(client: Client) -> None:
    """An operator can record a cheki and list the same day."""
    operator = _account(Role.OPERATOR.value)
    visit = _visit(operator)

    response = client.post(
        "/api/operator/cheki/",
        data={
            "visit_id": str(visit.id),
            "cast_id": "mio",
            "cheki_type": "basic",
            "quantity": 2,
        },
        content_type="application/json",
        headers=_auth(operator),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["cast_id"] == "mio"
    assert body["settlement_status"] == "candidate"

    list_response = client.get("/api/operator/cheki/", headers=_auth(operator))
    assert list_response.status_code == 200
    assert [row["id"] for row in list_response.json()] == [body["id"]]


def test_create_rejects_unknown_type(client: Client) -> None:
    """An unknown cheki_type returns 400 before any row is written."""
    operator = _account(Role.OPERATOR.value)
    visit = _visit(operator)

    response = client.post(
        "/api/operator/cheki/",
        data={
            "visit_id": str(visit.id),
            "cast_id": "mio",
            "cheki_type": "bogus",
            "quantity": 1,
        },
        content_type="application/json",
        headers=_auth(operator),
    )

    assert response.status_code == 400


def test_patch_cheki(client: Client) -> None:
    """An operator can correct quantity."""
    operator = _account(Role.OPERATOR.value)
    visit = _visit(operator)
    record = record_cheki(
        visit=visit, cast_id="mio", cheki_type="basic", quantity=1, actor=operator
    )

    response = client.patch(
        f"/api/operator/cheki/{record.id}",
        data={"quantity": 4},
        content_type="application/json",
        headers=_auth(operator),
    )

    assert response.status_code == 200
    assert response.json()["quantity"] == 4


def test_void_cheki_and_revoid_rejected(client: Client) -> None:
    """Voiding requires a reason and a second void returns 400."""
    operator = _account(Role.OPERATOR.value)
    visit = _visit(operator)
    record = record_cheki(
        visit=visit, cast_id="mio", cheki_type="basic", quantity=1, actor=operator
    )
    headers = _auth(operator)

    first = client.post(
        f"/api/operator/cheki/{record.id}/void",
        data={"reason": "duplicate"},
        content_type="application/json",
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["status"] == ChekiRecordStatus.VOIDED.value

    second = client.post(
        f"/api/operator/cheki/{record.id}/void",
        data={"reason": "again"},
        content_type="application/json",
        headers=headers,
    )
    assert second.status_code == 400


def test_permission_denied_for_fan_token(client: Client) -> None:
    """A valid non-staff token cannot access operator cheki routes."""
    fan = _account(Role.FAN.value)
    response = client.get("/api/operator/cheki/", headers=_auth(fan))
    assert response.status_code in {401, 403}


def test_missing_visit_returns_404(client: Client) -> None:
    """Recording against an unknown visit UUID returns 404."""
    operator = _account(Role.OPERATOR.value)
    response = client.post(
        "/api/operator/cheki/",
        data={
            "visit_id": "00000000-0000-0000-0000-000000000000",
            "cast_id": "mio",
            "cheki_type": "basic",
            "quantity": 1,
        },
        content_type="application/json",
        headers=_auth(operator),
    )
    assert response.status_code == 404


def test_voided_cheki_listed(client: Client) -> None:
    """The day list includes voided cheki records with status exposed."""
    operator = _account(Role.OPERATOR.value)
    visit = _visit(operator)
    record = record_cheki(
        visit=visit, cast_id="mio", cheki_type="basic", quantity=1, actor=operator
    )
    void_cheki(record=record, reason="bad", actor=operator)

    response = client.get("/api/operator/cheki/", headers=_auth(operator))
    assert response.status_code == 200
    assert response.json()[0]["status"] == ChekiRecordStatus.VOIDED.value
