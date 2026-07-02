"""API tests for operator schedule management (ASS-93)."""

from __future__ import annotations

from datetime import date, time

import pytest
from django.test import Client

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.schedule.models import ScheduleStatus
from apps.schedule.services import create_entry, publish_entry, request_change

pytestmark = pytest.mark.django_db


def _op() -> Account:
    """Create an operator account."""
    return Account.objects.create(role=Role.OPERATOR.value)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    token = issue_token_pair(account).access_token
    return {"authorization": f"Bearer {token}"}


def _payload() -> dict[str, str]:
    """A valid create payload."""
    return {
        "work_date": "2026-06-20",
        "cast_id": "mio",
        "start_time": "18:00:00",
        "end_time": "22:00:00",
        "note": "정상 출근",
    }


def test_create_list_publish(client: Client) -> None:
    """Create a draft, list it, and publish it."""
    op = _op()
    created = client.post(
        "/api/operator/schedule/entries",
        data=_payload(),
        content_type="application/json",
        headers=_auth(op),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == ScheduleStatus.DRAFT.value
    entry_id = body["id"]

    listed = client.get(
        "/api/operator/schedule/entries",
        data={"date": "2026-06-20"},
        headers=_auth(op),
    )
    assert listed.status_code == 200
    assert [r["id"] for r in listed.json()] == [entry_id]

    published = client.post(
        f"/api/operator/schedule/entries/{entry_id}/publish", headers=_auth(op)
    )
    assert published.status_code == 200
    assert published.json()["status"] == ScheduleStatus.PUBLISHED.value


def test_change_approval_flow_separation_of_duties(client: Client) -> None:
    """A published change needs a different operator to approve."""
    requester = _op()
    approver = _op()
    entry = create_entry(
        work_date=date(2026, 6, 20),
        cast_id="mio",
        start_time=time(18, 0),
        end_time=time(22, 0),
        actor=requester,
    )
    publish_entry(entry, actor=requester)

    change = request_change(
        entry=entry, proposed={"note": "변경"}, reason="r", actor=requester
    )

    # Requester approving own change → 400.
    self_approve = client.post(
        f"/api/operator/schedule/changes/{change.id}/approve",
        data={"decision_note": "self"},
        content_type="application/json",
        headers=_auth(requester),
    )
    assert self_approve.status_code == 400

    # Different operator approves → 200, change applied.
    ok = client.post(
        f"/api/operator/schedule/changes/{change.id}/approve",
        data={"decision_note": "ok"},
        content_type="application/json",
        headers=_auth(approver),
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "approved"


def test_change_request_on_draft_rejected(client: Client) -> None:
    """A change request against a draft entry returns 400."""
    op = _op()
    created = client.post(
        "/api/operator/schedule/entries",
        data=_payload(),
        content_type="application/json",
        headers=_auth(op),
    )
    entry_id = created.json()["id"]
    response = client.post(
        f"/api/operator/schedule/entries/{entry_id}/changes",
        data={"proposed": {"note": "x"}, "reason": "r"},
        content_type="application/json",
        headers=_auth(op),
    )
    assert response.status_code == 400


def test_list_changes_rejects_invalid_status(client: Client) -> None:
    """An unknown status filter on the change log returns 400, not a silent empty list."""
    op = _op()
    response = client.get(
        "/api/operator/schedule/changes",
        data={"status": "bogus"},
        headers=_auth(op),
    )
    assert response.status_code == 400


def test_permission_denied_for_fan(client: Client) -> None:
    """A fan token cannot access operator schedule routes."""
    fan = Account.objects.create(role=Role.FAN.value)
    response = client.get("/api/operator/schedule/entries", headers=_auth(fan))
    assert response.status_code in {401, 403}
