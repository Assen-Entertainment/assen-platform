"""Service tests for safety reports + blocks (ASS-96).

The safety-critical assertions: the narrative is stored only in the restricted
detail and never reaches the event payload, severity drives manager_only
visibility, and every mutation writes an audit entry.
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEntry
from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account, Role
from apps.safety.models import (
    BlockStatus,
    ReportStatus,
    ReportVisibility,
    SafetyReport,
    SafetyReportDetail,
)
from apps.safety.services import (
    block_user,
    change_report_status,
    file_report,
    lift_block,
    resolve_report,
)

pytestmark = pytest.mark.django_db

_SECRET = "그 사람이 사적 연락처를 계속 요구했어요 010-0000-0000"


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _file(
    actor: Account, *, severity: str = "low", target: Account | None = None
) -> SafetyReport:
    """File a report with a sensitive narrative for assertions."""
    return file_report(
        report_type="private_contact",
        severity=severity,
        reporter_type="fan",
        target_type="fan",
        narrative=_SECRET,
        actor=actor,
        target=target,
    )


def test_file_report_keeps_narrative_out_of_the_event() -> None:
    """The narrative lives only in the restricted detail, never in the event."""
    operator = _account(Role.OPERATOR.value)
    target = _account(Role.FAN.value)

    report = _file(operator, severity="low", target=target)

    detail = SafetyReportDetail.objects.get(report=report)
    assert detail.narrative == _SECRET
    assert report.visibility == ReportVisibility.RESTRICTED.value

    event = EventRecord.objects.get(event_name=EventName.SAFETY_REPORT_CREATED.value)
    # The secret must not appear anywhere in the serialised event.
    serialised = str(event.payload) + str(event.ids) + str(event.context)
    assert _SECRET not in serialised
    assert "010-0000-0000" not in serialised
    assert event.payload["report_type"] == "private_contact"
    assert event.payload["visibility"] == ReportVisibility.RESTRICTED.value
    AuditEntry.objects.get(action=AuditAction.SAFETY_REPORT_CREATED.value)


def test_high_severity_is_manager_only() -> None:
    """High/critical reports are visibility=manager_only."""
    operator = _account(Role.OPERATOR.value)
    report = _file(operator, severity="high")
    assert report.visibility == ReportVisibility.MANAGER_ONLY.value


def test_change_status_and_resolve() -> None:
    """Status advances, then resolve closes + emits resolved + stores the note."""
    operator = _account(Role.OPERATOR.value)
    manager = _account(Role.MANAGER.value)
    report = _file(operator)

    change_report_status(report=report, status=ReportStatus.REVIEWING.value, actor=operator)
    assert report.status == ReportStatus.REVIEWING.value
    AuditEntry.objects.get(action=AuditAction.SAFETY_REPORT_STATUS_CHANGED.value)

    resolve_report(
        report=report,
        resolution="actioned_block",
        resolution_note="차단 처리함",
        actor=manager,
    )
    report.refresh_from_db()
    assert report.status == ReportStatus.CLOSED.value
    assert report.detail.resolution_note == "차단 처리함"
    event = EventRecord.objects.get(event_name=EventName.SAFETY_REPORT_RESOLVED.value)
    assert event.payload["resolution"] == "actioned_block"
    # The restricted note must not leak into the event.
    assert "차단 처리함" not in str(event.payload)


def test_change_status_rejects_closed() -> None:
    """Closing must go through resolve_report, not change_report_status."""
    operator = _account(Role.OPERATOR.value)
    report = _file(operator)
    with pytest.raises(ValueError):
        change_report_status(
            report=report, status=ReportStatus.CLOSED.value, actor=operator
        )


def test_block_user_and_lift() -> None:
    """Blocking emits user_blocked + audit; lifting flips status (never deletes)."""
    manager = _account(Role.MANAGER.value)
    target = _account(Role.FAN.value)

    block = block_user(
        target=target,
        block_scope="reservation",
        block_reason="harassment",
        effective_from=timezone.now(),
        actor=manager,
    )
    assert block.status == BlockStatus.ACTIVE.value
    AuditEntry.objects.get(action=AuditAction.USER_BLOCKED.value)
    event = EventRecord.objects.get(event_name=EventName.USER_BLOCKED.value)
    assert event.payload["block_scope"] == "reservation"
    assert event.fan_id == str(target.fan_id)

    lift_block(block=block, reason="appeal upheld", actor=manager)
    block.refresh_from_db()
    assert block.status == BlockStatus.LIFTED.value
    AuditEntry.objects.get(action=AuditAction.USER_UNBLOCKED.value)

    with pytest.raises(ValueError):
        lift_block(block=block, reason="again", actor=manager)


def test_risk_flag_uses_distinct_audit_action() -> None:
    """A risk flag is audited as USER_RISK_FLAGGED, not USER_BLOCKED."""
    manager = _account(Role.MANAGER.value)
    target = _account(Role.FAN.value)

    block_user(
        target=target,
        block_scope="fandom_feature",
        block_reason="safety_risk",
        effective_from=timezone.now(),
        actor=manager,
        is_risk_flag=True,
    )
    AuditEntry.objects.get(action=AuditAction.USER_RISK_FLAGGED.value)
    assert not AuditEntry.objects.filter(
        action=AuditAction.USER_BLOCKED.value
    ).exists()
