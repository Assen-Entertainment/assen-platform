"""API tests for safety endpoints (ASS-96) — focused on the RBAC two-tier gate.

These prove the load-bearing access rules: an operator may file and list reports
but never sees the restricted detail or narrative; a manager may read the
narrative (audited) and resolve/block; non-managers are refused those routes.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.admin_rbac.redaction import REDACTED
from apps.audit.models import AuditAction, AuditEntry
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.safety.models import SafetyReport
from apps.safety.services import file_report

pytestmark = pytest.mark.django_db

_SECRET = "민감한 신고 서사 — 연락처 포함"


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    token = issue_token_pair(account).access_token
    return {"authorization": f"Bearer {token}"}


def _seed_report(operator: Account) -> SafetyReport:
    """File a high-severity (manager_only) report with a secret narrative."""
    return file_report(
        report_type="stalking_concern",
        severity="high",
        reporter_type="fan",
        target_type="fan",
        narrative=_SECRET,
        actor=operator,
        target=_account(Role.FAN.value),
    )


def test_operator_files_and_lists_with_detail_redacted(client: Client) -> None:
    """An operator files a report and lists it with detail fields redacted."""
    operator = _account(Role.OPERATOR.value)

    created = client.post(
        "/api/safety/reports",
        data={
            "report_type": "verbal_abuse",
            "severity": "medium",
            "reporter_type": "fan",
            "target_type": "cast",
            "narrative": _SECRET,
        },
        content_type="application/json",
        headers=_auth(operator),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["report_type"] == "verbal_abuse"
    # Detail fields are redacted for an operator.
    assert body["detail_ref"] == REDACTED
    assert body["reporter_id"] == REDACTED

    listed = client.get("/api/safety/reports", headers=_auth(operator))
    assert listed.status_code == 200
    assert listed.json()[0]["detail_ref"] == REDACTED


def test_operator_cannot_read_detail(client: Client) -> None:
    """The restricted narrative endpoint is manager+ only."""
    operator = _account(Role.OPERATOR.value)
    report = _seed_report(operator)

    response = client.get(
        f"/api/safety/reports/{report.id}/detail", headers=_auth(operator)
    )
    assert response.status_code in {401, 403}


def test_manager_reads_detail_and_it_is_audited(client: Client) -> None:
    """A manager reads the narrative and the read writes a SAFETY_DETAIL_VIEWED audit."""
    operator = _account(Role.OPERATOR.value)
    manager = _account(Role.MANAGER.value)
    report = _seed_report(operator)

    response = client.get(
        f"/api/safety/reports/{report.id}/detail",
        data={"reason": "triage review"},
        headers=_auth(manager),
    )
    assert response.status_code == 200
    assert response.json()["narrative"] == _SECRET
    audit = AuditEntry.objects.get(
        action=AuditAction.SAFETY_DETAIL_VIEWED.value, target=str(report.id)
    )
    assert audit.reason == "triage review"


def test_operator_cannot_resolve_or_block(client: Client) -> None:
    """Resolve and block are manager+ only."""
    operator = _account(Role.OPERATOR.value)
    report = _seed_report(operator)

    resolve = client.post(
        f"/api/safety/reports/{report.id}/resolve",
        data={"resolution": "x", "resolution_note": "y"},
        content_type="application/json",
        headers=_auth(operator),
    )
    assert resolve.status_code in {401, 403}

    block = client.post(
        "/api/safety/blocks",
        data={
            "target_id": str(_account(Role.FAN.value).fan_id),
            "block_scope": "reservation",
            "block_reason": "r",
        },
        content_type="application/json",
        headers=_auth(operator),
    )
    assert block.status_code in {401, 403}


def test_manager_resolves_and_blocks(client: Client) -> None:
    """A manager can resolve a report and block a fan."""
    operator = _account(Role.OPERATOR.value)
    manager = _account(Role.MANAGER.value)
    report = _seed_report(operator)
    target = _account(Role.FAN.value)

    resolve = client.post(
        f"/api/safety/reports/{report.id}/resolve",
        data={"resolution": "actioned_block", "resolution_note": "처리"},
        content_type="application/json",
        headers=_auth(manager),
    )
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "closed"

    block = client.post(
        "/api/safety/blocks",
        data={
            "target_id": str(target.fan_id),
            "block_scope": "reservation",
            "block_reason": "harassment",
        },
        content_type="application/json",
        headers=_auth(manager),
    )
    assert block.status_code == 201
    assert block.json()["block_scope"] == "reservation"


def test_block_reason_must_be_enum(client: Client) -> None:
    """Free-text block_reason is rejected so PII cannot leak into the event log."""
    manager = _account(Role.MANAGER.value)
    target = _account(Role.FAN.value)

    response = client.post(
        "/api/safety/blocks",
        data={
            "target_id": str(target.fan_id),
            "block_scope": "reservation",
            "block_reason": "피해자 이름과 연락처 010-0000-0000",
        },
        content_type="application/json",
        headers=_auth(manager),
    )
    assert response.status_code == 400


def test_detail_requires_reason(client: Client) -> None:
    """Reading the restricted narrative without a reason is rejected (audit needs why)."""
    operator = _account(Role.OPERATOR.value)
    manager = _account(Role.MANAGER.value)
    report = _seed_report(operator)

    response = client.get(
        f"/api/safety/reports/{report.id}/detail", headers=_auth(manager)
    )
    assert response.status_code in {400, 422}


def test_unknown_report_type_rejected(client: Client) -> None:
    """An unknown report_type returns 400 before any row is written."""
    operator = _account(Role.OPERATOR.value)
    response = client.post(
        "/api/safety/reports",
        data={
            "report_type": "bogus",
            "severity": "low",
            "reporter_type": "fan",
            "target_type": "fan",
        },
        content_type="application/json",
        headers=_auth(operator),
    )
    assert response.status_code == 400
    assert not SafetyReport.objects.exists()
