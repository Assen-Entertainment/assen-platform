"""Tests for the operator POS-link API (ASS-102 v0).

Covers create/list/void, the coverage (연결률) surface, operator gating, and
input validation on the wired HTTP surface.
"""

from __future__ import annotations

import json
import uuid

import pytest
from django.test import Client
from django.utils import timezone

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.pos_lite.services import link_pos_order
from apps.visit.models import VisitRecord
from apps.visit.services import record_visit

pytestmark = pytest.mark.django_db

ORDERS = "/api/operator/pos/orders"
COVERAGE = "/api/operator/pos/coverage"
JSON = "application/json"


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _visit(operator: Account, fan: Account) -> VisitRecord:
    """Record a manual visit to link a POS order against."""
    return record_visit(fan=fan, visited_at=timezone.now(), actor=operator)


def test_operator_can_link_and_list(client: Client) -> None:
    """An operator links a POS order and sees it in the day's list."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)

    created = client.post(
        ORDERS,
        data=json.dumps(
            {
                "visit_id": str(visit.id),
                "pos_receipt_no": "R-100",
                "payment_status": "paid",
                "payment_method": "card",
                "amount": 15000,
            }
        ),
        content_type=JSON,
        headers=_auth(op),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["pos_receipt_no"] == "R-100"
    assert body["payment_status"] == "paid"
    assert body["link_method"] == "manual"

    listed = client.get(ORDERS, headers=_auth(op))
    assert listed.status_code == 200
    assert any(row["pos_receipt_no"] == "R-100" for row in listed.json())


def test_link_unknown_visit_returns_404(client: Client) -> None:
    """Linking against a non-existent visit is a 404."""
    op = _account(Role.OPERATOR.value)
    res = client.post(
        ORDERS,
        data=json.dumps({"visit_id": str(uuid.uuid4()), "pos_receipt_no": "R"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 404


def test_link_without_reference_is_400(client: Client) -> None:
    """A link with neither receipt nor order number is rejected."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    res = client.post(
        ORDERS,
        data=json.dumps({"visit_id": str(visit.id)}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 400


def test_duplicate_receipt_is_400(client: Client) -> None:
    """A duplicate active receipt is rejected at the API."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit_a = _visit(op, fan)
    visit_b = _visit(op, fan)
    first = client.post(
        ORDERS,
        data=json.dumps({"visit_id": str(visit_a.id), "pos_receipt_no": "D"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert first.status_code == 201
    dup = client.post(
        ORDERS,
        data=json.dumps({"visit_id": str(visit_b.id), "pos_receipt_no": "D"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert dup.status_code == 400


def test_void_endpoint(client: Client) -> None:
    """An operator voids a POS link with a reason."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    order = link_pos_order(visit=visit, actor=op, pos_receipt_no="R-V")

    res = client.post(
        f"{ORDERS}/{order.id}/void",
        data=json.dumps({"reason": "entered twice"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "voided"


def test_coverage_reports_link_rate(client: Client) -> None:
    """Coverage counts linked vs total active visits and lists the unlinked."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    linked_visit = _visit(op, fan)
    unlinked_visit = _visit(op, fan)
    link_pos_order(visit=linked_visit, actor=op, pos_receipt_no="R-COV")

    res = client.get(COVERAGE, headers=_auth(op))
    assert res.status_code == 200
    body = res.json()
    assert body["total_active_visits"] == 2
    assert body["linked_visits"] == 1
    assert body["unlinked_visits"] == 1
    assert body["link_rate"] == 0.5
    assert [u["visit_id"] for u in body["unlinked"]] == [str(unlinked_visit.id)]


def test_list_filters_by_business_day(client: Client) -> None:
    """A link created with an explicit business_day lists under that day only."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    client.post(
        ORDERS,
        data=json.dumps(
            {"visit_id": str(visit.id), "pos_receipt_no": "R-BD", "business_day": "2026-03-02"}
        ),
        content_type=JSON,
        headers=_auth(op),
    )

    on_day = client.get(f"{ORDERS}?date=2026-03-02", headers=_auth(op))
    assert any(r["pos_receipt_no"] == "R-BD" for r in on_day.json())
    today = client.get(ORDERS, headers=_auth(op))
    assert not any(r["pos_receipt_no"] == "R-BD" for r in today.json())


def test_fan_and_anonymous_are_refused(client: Client) -> None:
    """The POS endpoints are operator-gated."""
    fan = _account(Role.FAN.value)
    assert client.get(ORDERS, headers=_auth(fan)).status_code in {401, 403}
    assert client.get(ORDERS).status_code in {401, 403}
    assert client.get(COVERAGE, headers=_auth(fan)).status_code in {401, 403}


def test_unknown_payment_status_is_400(client: Client) -> None:
    """An out-of-domain payment_status surfaces as a 400."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    visit = _visit(op, fan)
    res = client.post(
        ORDERS,
        data=json.dumps(
            {"visit_id": str(visit.id), "pos_receipt_no": "R-Z", "payment_status": "x"}
        ),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 400
