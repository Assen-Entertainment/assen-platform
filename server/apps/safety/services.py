"""Service layer for operator safety reports and user blocks (ASS-96).

The load-bearing safety rule: the reporter's **narrative and any PII go only to
:class:`~apps.safety.models.SafetyReportDetail`** (the restricted store). Events
carry classification + ids only — ``emit_event`` additionally rejects narrative
keys for safety events (``FORBIDDEN_SAFETY_PROPERTY_KEYS``), so a leak fails
loudly rather than silently. Every state change writes an audit entry, and
reports/blocks are status-changed, never deleted (Data 제약).

Access control is enforced at the API boundary (operator may file/list with
detail redacted; manager+ may read detail / resolve / block); these services
assume the caller is already authorised.
"""

from __future__ import annotations

from datetime import datetime

from django.db import transaction

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.event_log.events import ActorType, EventName, EventSource, EventStatus
from apps.event_log.services import emit_event
from apps.identity.models import Account
from apps.safety.models import (
    ActorKind,
    BlockStatus,
    ReportSeverity,
    ReportStatus,
    ReportVisibility,
    SafetyReport,
    SafetyReportDetail,
    UserBlock,
)

# Severities whose reports are visible to manager+ only.
_MANAGER_ONLY_SEVERITIES = frozenset(
    {ReportSeverity.HIGH.value, ReportSeverity.CRITICAL.value}
)


def _visibility_for(severity: str) -> str:
    """High/critical reports are manager_only; the rest are restricted."""
    if severity in _MANAGER_ONLY_SEVERITIES:
        return ReportVisibility.MANAGER_ONLY.value
    return ReportVisibility.RESTRICTED.value


def _event_fan_id(report: SafetyReport) -> str:
    """The fan_id for the event envelope, if a fan is involved (조건부)."""
    if report.target_type == ActorKind.FAN.value and report.target is not None:
        return str(report.target.fan_id)
    if report.reporter_type == ActorKind.FAN.value and report.reporter is not None:
        return str(report.reporter.fan_id)
    return ""


@transaction.atomic
def file_report(
    *,
    report_type: str,
    severity: str,
    reporter_type: str,
    target_type: str,
    narrative: str,
    actor: Account,
    reporter: Account | None = None,
    target: Account | None = None,
    cast_id: str = "",
    visit_id: str = "",
) -> SafetyReport:
    """Create a safety report (summary) + its restricted detail, and emit event.

    The narrative is written only to :class:`SafetyReportDetail`; the
    ``safety_report_created`` event and the summary row carry classification and
    ids only.
    """
    report = SafetyReport.objects.create(
        report_type=report_type,
        severity=severity,
        visibility=_visibility_for(severity),
        reporter_type=reporter_type,
        target_type=target_type,
        reporter=reporter,
        target=target,
        cast_id=cast_id,
        visit_id=visit_id or None,
        created_by=actor,
    )
    SafetyReportDetail.objects.create(report=report, narrative=narrative)
    record_audit(
        actor=actor,
        action=AuditAction.SAFETY_REPORT_CREATED.value,
        target=str(report.id),
        metadata={
            "report_type": report_type,
            "severity": severity,
            "visibility": report.visibility,
        },
    )
    emit_event(
        event_name=EventName.SAFETY_REPORT_CREATED.value,
        occurred_at=report.created_at,
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_id=str(actor.fan_id),
        fan_id=_event_fan_id(report),
        cast_id=cast_id,
        visit_id=str(visit_id) if visit_id else "",
        actor_is_operator=True,
        ids={"safety_report_id": str(report.id)},
        # Classification + visibility + ids only — never the narrative.
        payload={
            "safety_report_id": str(report.id),
            "reporter_type": reporter_type,
            "target_type": target_type,
            "report_type": report_type,
            "severity": severity,
            "visibility": report.visibility,
        },
    )
    return report


@transaction.atomic
def change_report_status(
    *, report: SafetyReport, status: str, actor: Account
) -> SafetyReport:
    """Advance the report's handling status with an audit entry.

    Closing is done via :func:`resolve_report` (which also emits the resolved
    event); this covers the received→reviewing→actioned transitions.
    """
    if status == ReportStatus.CLOSED.value:
        raise ValueError("Use resolve_report to close a report.")
    if report.status == ReportStatus.CLOSED.value:
        # A resolved safety case must not be silently reopened (symmetry with
        # resolve_report / lift_block rejecting already-terminal states).
        raise ValueError("Closed report cannot change status.")
    before = report.status
    report.status = status
    report.save(update_fields=["status", "updated_at"])
    record_audit(
        actor=actor,
        action=AuditAction.SAFETY_REPORT_STATUS_CHANGED.value,
        target=str(report.id),
        metadata={"before": before, "after": status},
    )
    return report


@transaction.atomic
def resolve_report(
    *, report: SafetyReport, resolution: str, resolution_note: str, actor: Account
) -> SafetyReport:
    """Close a report: set status, store the note in the restricted detail, emit.

    ``resolution`` is a short classification carried by the event; the free-text
    ``resolution_note`` is stored only in the restricted detail.
    """
    if report.status == ReportStatus.CLOSED.value:
        raise ValueError("Report is already closed.")
    report.status = ReportStatus.CLOSED.value
    report.save(update_fields=["status", "updated_at"])
    detail = report.detail
    detail.resolution_note = resolution_note
    detail.save(update_fields=["resolution_note", "updated_at"])
    record_audit(
        actor=actor,
        action=AuditAction.SAFETY_REPORT_RESOLVED.value,
        target=str(report.id),
        metadata={"resolution": resolution},
    )
    emit_event(
        event_name=EventName.SAFETY_REPORT_RESOLVED.value,
        occurred_at=report.updated_at,
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_id=str(actor.fan_id),
        fan_id=_event_fan_id(report),
        actor_is_operator=True,
        status=EventStatus.RESOLVED.value,
        ids={"safety_report_id": str(report.id)},
        payload={"safety_report_id": str(report.id), "resolution": resolution},
    )
    return report


@transaction.atomic
def block_user(
    *,
    target: Account,
    block_scope: str,
    block_reason: str,
    effective_from: datetime,
    actor: Account,
    is_risk_flag: bool = False,
    source_report: SafetyReport | None = None,
) -> UserBlock:
    """Create a block (or risk flag) on a fan and emit ``user_blocked``.

    A risk flag is a lighter limit (no hard block) but follows the same
    accountability path. The block_reason is a short operator-entered string, not
    a narrative.
    """
    block = UserBlock.objects.create(
        target=target,
        block_scope=block_scope,
        block_reason=block_reason,
        is_risk_flag=is_risk_flag,
        effective_from=effective_from,
        source_report=source_report,
        created_by=actor,
    )
    record_audit(
        actor=actor,
        action=(
            AuditAction.USER_RISK_FLAGGED.value
            if is_risk_flag
            else AuditAction.USER_BLOCKED.value
        ),
        target=str(target.fan_id),
        reason=block_reason,
        metadata={"block_id": str(block.id), "block_scope": block_scope},
    )
    emit_event(
        event_name=EventName.USER_BLOCKED.value,
        occurred_at=block.created_at,
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_id=str(actor.fan_id),
        fan_id=str(target.fan_id),
        actor_is_operator=True,
        ids={"block_id": str(block.id), "fan_id": str(target.fan_id)},
        payload={
            "block_id": str(block.id),
            "block_scope": block_scope,
            "block_reason": block_reason,
            "effective_from": effective_from.isoformat(),
        },
    )
    return block


@transaction.atomic
def lift_block(*, block: UserBlock, reason: str, actor: Account) -> UserBlock:
    """Lift an active block (status→lifted, never deleted) with an audit entry."""
    if block.status == BlockStatus.LIFTED.value:
        raise ValueError("Block is already lifted.")
    if not reason.strip():
        raise ValueError("Lift reason is required.")
    block.status = BlockStatus.LIFTED.value
    block.lifted_reason = reason.strip()
    block.save(update_fields=["status", "lifted_reason", "updated_at"])
    record_audit(
        actor=actor,
        action=AuditAction.USER_UNBLOCKED.value,
        target=str(block.target.fan_id),
        reason=block.lifted_reason,
        metadata={"block_id": str(block.id)},
    )
    return block
