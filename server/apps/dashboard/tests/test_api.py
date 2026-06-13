"""Acceptance tests for the operator dashboard API (ASS-97 v0)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEntry
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.visit.services import record_visit

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    token = issue_token_pair(account).access_token
    return {"authorization": f"Bearer {token}"}


def test_dashboard_counts_today_and_logs_usage(client: Client) -> None:
    """The dashboard projects today's check-ins and logs the view as usage."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    now = timezone.now()
    record_visit(fan=fan, visited_at=now, actor=operator)
    record_visit(fan=fan, visited_at=now, actor=operator)

    response = client.get("/api/operator/dashboard/", headers=_auth(operator))

    assert response.status_code == 200
    body = response.json()
    assert body["visits"] == 2
    # No cheki/reservation/favorite/safety events were emitted.
    assert body["cheki"] == 0
    assert body["reservations"] == 0
    assert body["safety_reports_open"] == 0
    assert body["business_day"] == timezone.localdate().isoformat()

    # Acceptance: the view is recorded so weekly usage is measurable.
    assert AuditEntry.objects.filter(
        action=AuditAction.DASHBOARD_VIEWED.value, actor=operator
    ).exists()


def test_dashboard_scopes_counts_to_the_requested_day(client: Client) -> None:
    """A visit on another day is not counted in today's window."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    yesterday = timezone.now() - timedelta(days=1)
    record_visit(fan=fan, visited_at=yesterday, actor=operator)

    today_resp = client.get("/api/operator/dashboard/", headers=_auth(operator))
    assert today_resp.json()["visits"] == 0

    y_date = timezone.localdate() - timedelta(days=1)
    y_resp = client.get(
        "/api/operator/dashboard/",
        data={"date": y_date.isoformat()},
        headers=_auth(operator),
    )
    assert y_resp.json()["visits"] == 1


def test_dashboard_is_operator_gated(client: Client) -> None:
    """A fan token cannot read the operator dashboard."""
    fan = _account(Role.FAN.value)
    response = client.get("/api/operator/dashboard/", headers=_auth(fan))
    assert response.status_code in {401, 403}
