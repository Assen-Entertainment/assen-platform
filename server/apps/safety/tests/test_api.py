"""API tests for safety endpoints (ASS-96) — focused on the RBAC two-tier gate.

These prove the load-bearing access rules: an operator may file and list reports
but never sees the restricted detail or narrative; a manager may read the
narrative (audited) and resolve/block; non-managers are refused those routes.
"""

from __future__ import annotations

import uuid

import pytest
from django.test import Client

from apps.admin_rbac.redaction import REDACTED
from apps.audit.models import AuditAction, AuditEntry
from apps.cast.models import CastProfile
from apps.event_log.models import EventRecord
from apps.identity.cookies import ACCESS_COOKIE_NAME
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

    response = client.get(f"/api/safety/reports/{report.id}/detail", headers=_auth(operator))
    assert response.status_code in {401, 403}


def test_manager_reads_detail_and_it_is_audited(client: Client) -> None:
    """A manager reads the narrative and the read writes a SAFETY_DETAIL_VIEWED audit."""
    operator = _account(Role.OPERATOR.value)
    manager = _account(Role.MANAGER.value)
    report = _seed_report(operator)

    response = client.get(
        f"/api/safety/reports/{report.id}/detail",
        data={"reason": "report_triage"},
        headers=_auth(manager),
    )
    assert response.status_code == 200
    assert response.json()["narrative"] == _SECRET
    audit = AuditEntry.objects.get(
        action=AuditAction.SAFETY_DETAIL_VIEWED.value, target=str(report.id)
    )
    # The audit trail records the closed reason CODE, never free text (ASS-291 #7).
    assert audit.reason == "report_triage"


def test_detail_reason_must_be_a_closed_code(client: Client) -> None:
    """A free-text detail-access reason is refused so PII can't ride the query string.

    The "why" now travels as a bounded reason CODE; a free-text reason carrying a
    name/phone is rejected (400), never recorded, and never echoed back (ASS-291 #7).
    """
    manager = _account(Role.MANAGER.value)
    report = _seed_report(_account(Role.OPERATOR.value))

    response = client.get(
        f"/api/safety/reports/{report.id}/detail",
        data={"reason": "피해자 이름 010-0000-0000 확인차"},
        headers=_auth(manager),
    )
    assert response.status_code == 400
    assert "010-0000-0000" not in response.content.decode()
    assert not AuditEntry.objects.filter(
        action=AuditAction.SAFETY_DETAIL_VIEWED.value
    ).exists()


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

    response = client.get(f"/api/safety/reports/{report.id}/detail", headers=_auth(manager))
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


# --- operator cast_id validation (ASS-291 #7) -------------------------------- #

_REPORT_BASE = {
    "report_type": "verbal_abuse",
    "severity": "medium",
    "reporter_type": "fan",
    "target_type": "cast",
    "narrative": _SECRET,
}


def test_create_report_rejects_malformed_cast_id(client: Client) -> None:
    """A cast_id that isn't a well-formed cast id is refused before any row is written.

    The operator-supplied cast_id is written verbatim into the append-only event
    ledger; arbitrary free text (a name / phone) must never be persisted there
    (ASS-291 #7). No report or event is written, and the input is not echoed back.
    """
    operator = _account(Role.OPERATOR.value)
    response = client.post(
        "/api/safety/reports",
        data={**_REPORT_BASE, "cast_id": "홍길동 010-0000-0000"},
        content_type="application/json",
        headers=_auth(operator),
    )
    assert response.status_code == 400
    assert "010-0000-0000" not in response.content.decode()
    assert not SafetyReport.objects.exists()
    assert not EventRecord.objects.exists()


def test_create_report_rejects_unknown_cast_id(client: Client) -> None:
    """A well-formed but unknown cast_id (no such profile) is refused (400)."""
    operator = _account(Role.OPERATOR.value)
    response = client.post(
        "/api/safety/reports",
        data={**_REPORT_BASE, "cast_id": str(uuid.uuid4())},
        content_type="application/json",
        headers=_auth(operator),
    )
    assert response.status_code == 400
    assert not SafetyReport.objects.exists()
    assert not EventRecord.objects.exists()


def test_create_report_accepts_existing_cast_id_onto_event(client: Client) -> None:
    """A well-formed cast_id of an existing profile is accepted and rides the event."""
    operator = _account(Role.OPERATOR.value)
    profile = CastProfile.objects.create(stage_name="스텔라", created_by=operator)
    response = client.post(
        "/api/safety/reports",
        data={**_REPORT_BASE, "cast_id": str(profile.id)},
        content_type="application/json",
        headers=_auth(operator),
    )
    assert response.status_code == 201
    event = EventRecord.objects.get(event_name="safety_report_created")
    assert event.cast_id == str(profile.id)


# --- Fan self-reporting (ASS-110, F11) --------------------------------------


def test_fan_files_report_and_gets_a_receipt_only(client: Client) -> None:
    """A fan files a report and receives a confirmation with no internal fields."""
    fan = _account(Role.FAN.value)
    response = client.post(
        "/api/safety/fan-reports",
        data={"report_type": "private_contact", "narrative": _SECRET},
        content_type="application/json",
        headers=_auth(fan),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["safety_report_id"]
    assert body["status"] == "received"
    # Receipt only: no severity/visibility/reporter/narrative leaked to the fan.
    assert set(body) == {"safety_report_id", "status", "created_at"}
    assert _SECRET not in response.content.decode()

    # The fan is the reporter; the narrative is in the restricted detail store.
    report = SafetyReport.objects.get(id=body["safety_report_id"])
    assert report.reporter == fan
    assert report.reporter_type == "fan"
    assert report.detail.narrative == _SECRET


def test_fan_report_requires_authentication(client: Client) -> None:
    """Filing a report without a token is refused."""
    response = client.post(
        "/api/safety/fan-reports",
        data={"report_type": "verbal_abuse"},
        content_type="application/json",
    )
    assert response.status_code in {401, 403}


def test_fan_report_rejects_non_fan_reportable_type(client: Client) -> None:
    """Operator/finance categories are not fan-reportable (422); no row written."""
    fan = _account(Role.FAN.value)
    response = client.post(
        "/api/safety/fan-reports",
        data={"report_type": "refund_dispute", "narrative": "x"},
        content_type="application/json",
        headers=_auth(fan),
    )
    assert response.status_code == 422
    assert not SafetyReport.objects.exists()


def test_fan_report_unknown_type_rejected(client: Client) -> None:
    """An unknown report_type is refused (422) before any row is written."""
    fan = _account(Role.FAN.value)
    response = client.post(
        "/api/safety/fan-reports",
        data={"report_type": "bogus"},
        content_type="application/json",
        headers=_auth(fan),
    )
    assert response.status_code == 422
    assert not SafetyReport.objects.exists()


def test_fan_filed_report_is_operator_visible_with_detail_redacted(
    client: Client,
) -> None:
    """A fan-filed report reaches the operator queue with its detail redacted."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    filed = client.post(
        "/api/safety/fan-reports",
        data={"report_type": "unwanted_request", "narrative": _SECRET},
        content_type="application/json",
        headers=_auth(fan),
    )
    report_id = filed.json()["safety_report_id"]

    listed = client.get("/api/safety/reports", headers=_auth(operator))
    assert listed.status_code == 200
    rows = {row["safety_report_id"]: row for row in listed.json()}
    assert report_id in rows
    assert rows[report_id]["detail_ref"] == REDACTED
    assert _SECRET not in listed.content.decode()


def test_staff_token_cannot_file_a_fan_report(client: Client) -> None:
    """fan_auth is role-agnostic, so the endpoint must reject a staff token (403).

    Otherwise an operator/manager token would file a report stamped reporter_type=
    fan / actor_is_operator=False, misclassifying operator traffic as a fan report.
    """
    for role in (Role.OPERATOR.value, Role.MANAGER.value):
        response = client.post(
            "/api/safety/fan-reports",
            data={"report_type": "verbal_abuse", "narrative": "x"},
            content_type="application/json",
            headers=_auth(_account(role)),
        )
        assert response.status_code == 403
    assert not SafetyReport.objects.exists()


def test_fan_supplied_severity_is_ignored_server_derives_it(client: Client) -> None:
    """A fan cannot downgrade a threat: an injected severity is dropped, not used."""
    fan = _account(Role.FAN.value)
    response = client.post(
        "/api/safety/fan-reports",
        # physical_threat must enter critical; the injected severity=low is ignored
        # (FanReportCreateIn has no severity field, so Ninja drops the extra key).
        data={"report_type": "physical_threat", "narrative": "x", "severity": "low"},
        content_type="application/json",
        headers=_auth(fan),
    )
    assert response.status_code == 201
    report = SafetyReport.objects.get(id=response.json()["safety_report_id"])
    assert report.severity == "critical"


def test_fan_report_invalid_type_error_does_not_echo_input(client: Client) -> None:
    """An invalid report_type must not be reflected back — no PII echo in the 422."""
    fan = _account(Role.FAN.value)
    response = client.post(
        "/api/safety/fan-reports",
        data={"report_type": "leak-010-9999-8888", "narrative": "x"},
        content_type="application/json",
        headers=_auth(fan),
    )
    assert response.status_code == 422
    assert "010-9999-8888" not in response.content.decode()
    assert not SafetyReport.objects.exists()


def test_fan_report_cookie_surface_with_csrf_is_201() -> None:
    """The web cookie surface can file a report when the CSRF token accompanies it (B3).

    Uses a CSRF-enforcing client: the fan's access token rides the web httpOnly
    cookie, and the ``/fan/csrf`` cookie is echoed in ``X-CSRFToken`` (the
    double-submit grace condition). ``fan_auth``'s cookie surface enforces CSRF on
    this unsafe POST, so a valid token yields 201.
    """
    csrf_client = Client(enforce_csrf_checks=True)
    fan = _account(Role.FAN.value)
    # Plant the access token as the web access cookie (cookie surface, not bearer).
    csrf_client.cookies[ACCESS_COOKIE_NAME] = issue_token_pair(fan).access_token
    # Obtain the CSRF cookie, then echo it back on the report POST.
    csrf_client.get("/api/fan/csrf")
    token = csrf_client.cookies["csrftoken"].value

    response = csrf_client.post(
        "/api/safety/fan-reports",
        data={"report_type": "private_contact", "narrative": _SECRET},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 201
    report = SafetyReport.objects.get(id=response.json()["safety_report_id"])
    assert report.reporter == fan
    assert report.reporter_type == "fan"
