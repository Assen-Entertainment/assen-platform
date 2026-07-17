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

This app is also the platform's media-moderation domain: a report may target an
uploaded image (``SafetyReport.upload``), and moving such a report to ``actioned``
takes that image down (:func:`change_report_status`). There is deliberately no
separate moderation queue for media — the operator report queue IS the queue.
"""

from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.event_log.events import ActorType, EventName, EventSource, EventStatus
from apps.event_log.services import emit_event
from apps.identity.models import Account
from apps.safety.models import (
    ActorKind,
    BlockScope,
    BlockStatus,
    ReportSeverity,
    ReportStatus,
    ReportType,
    ReportVisibility,
    SafetyReport,
    SafetyReportDetail,
    UserBlock,
)
from apps.uploads.models import Upload
from apps.uploads.services import restore_upload, take_down_upload


class SafetyReportError(Exception):
    """Raised when a self-filed safety report is rejected (e.g. unknown type)."""


def has_active_block(*, target: Account, scopes: list[str]) -> bool:
    """Whether [target] has an active hard block covering any of [scopes].

    A hard block (``status=active``, already effective, and not a soft
    ``is_risk_flag`` annotation) whose ``block_scope`` is one of [scopes] — or
    the catch-all ``all`` — restricts that feature surface. Feature surfaces
    (reservation, QR check-in, …) call this so a blocked fan is refused at the
    action rather than each surface re-deriving the "active block" predicate.
    """
    return UserBlock.objects.filter(
        target=target,
        status=BlockStatus.ACTIVE.value,
        is_risk_flag=False,
        effective_from__lte=timezone.now(),
        block_scope__in=[*scopes, BlockScope.ALL.value],
    ).exists()


# Severities whose reports are visible to manager+ only.
_MANAGER_ONLY_SEVERITIES = frozenset({ReportSeverity.HIGH.value, ReportSeverity.CRITICAL.value})


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


def _report_ids(report: SafetyReport) -> dict[str, str]:
    """Id map for the event envelope: the report, plus the upload when bound.

    Server-minted ids only — an Upload id carries no filename or PII, so it is safe
    for the append-only ledger and lets media takedowns be reconciled from events.
    """
    ids = {"safety_report_id": str(report.id)}
    if report.upload_id is not None:
        ids["upload_id"] = str(report.upload_id)
    return ids


# --- Fan self-reporting (ASS-110, F11) --------------------------------------

# The report types a fan may file directly from the app ("신고 유형 9종"). The
# operator/finance-side categories (refund_dispute, fraud_abuse) are excluded — a
# fan raises those through the refund/dispute flow, not a safety self-report.
FAN_REPORTABLE_TYPES: frozenset[str] = frozenset(
    {
        ReportType.UNWANTED_REQUEST.value,
        ReportType.PRIVATE_CONTACT.value,
        ReportType.EXTERNAL_MEETING.value,
        ReportType.VERBAL_ABUSE.value,
        ReportType.PHYSICAL_THREAT.value,
        ReportType.PHOTO_VIOLATION.value,
        ReportType.STALKING_CONCERN.value,
        ReportType.PRIVACY_PORTRAIT_CONCERN.value,
        ReportType.OTHER.value,
    }
)

# Severity a fan self-report ENTERS at, derived from the report type — a fan never
# sets severity (it is operator/manager judgement, Refusal_Report_Block_Protocol
# 역할표), operators re-triage afterwards. The mapping mirrors the protocol 심각도
# 기준: physical threat / stalking are critical; private contact, external meeting,
# photo-or-posting violation and verbal abuse are high; the rest enter at medium
# ("운영자가 판단하기 어려우면 낮게 보지 말고 한 단계 높게").
_FAN_REPORT_SEVERITY: dict[str, str] = {
    ReportType.PHYSICAL_THREAT.value: ReportSeverity.CRITICAL.value,
    ReportType.STALKING_CONCERN.value: ReportSeverity.CRITICAL.value,
    ReportType.PRIVATE_CONTACT.value: ReportSeverity.HIGH.value,
    ReportType.EXTERNAL_MEETING.value: ReportSeverity.HIGH.value,
    ReportType.PHOTO_VIOLATION.value: ReportSeverity.HIGH.value,
    ReportType.VERBAL_ABUSE.value: ReportSeverity.HIGH.value,
}
_FAN_REPORT_DEFAULT_SEVERITY = ReportSeverity.MEDIUM.value


def fan_report_severity(report_type: str) -> str:
    """Entry severity for a fan self-report of [report_type] (protocol-derived)."""
    return _FAN_REPORT_SEVERITY.get(report_type, _FAN_REPORT_DEFAULT_SEVERITY)


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
    upload: Upload | None = None,
) -> SafetyReport:
    """Create a safety report (summary) + its restricted detail, and emit event.

    The narrative is written only to :class:`SafetyReportDetail`; the
    ``safety_report_created`` event and the summary row carry classification and
    ids only.

    ``upload`` binds the report to an uploaded image when it is about one; taking that
    report to ``actioned`` then takes the image down (:func:`change_report_status`).
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
        upload=upload,
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
        ids=_report_ids(report),
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
def file_fan_report(
    *,
    reporter: Account,
    report_type: str,
    narrative: str = "",
    upload: Upload | None = None,
) -> SafetyReport:
    """File a safety report submitted directly by a fan (ASS-110, F11).

    The fan is both the actor and the reporter. Unlike the operator intake
    (:func:`file_report`), the severity is *derived* from the report type
    (:func:`fan_report_severity`) rather than caller-supplied, and the event is
    recorded as a fan action (``actor_is_operator=False``) so it is never mistaken
    for operator traffic in the metrics. The narrative goes only to the restricted
    :class:`SafetyReportDetail`; the event keeps classification + ids.

    No structured ``cast_id`` is taken from the fan: an untrusted free-string id
    would ride into the append-only event log (``EventRecord.cast_id``) and could
    carry the very PII the narrative isolation exists to contain. The fan names the
    cast in the narrative (restricted store) and an operator links the structured
    cast during triage, so a fan self-report always enters ``target_type=unknown``.

    Reporting stays available regardless of any block on the fan: a safety channel
    must not be closed to the person trying to use it. No staff audit row is
    written (the fan is not staff) — the append-only ``safety_report_created``
    event is the record of intake.

    Idempotency: intake is deliberately not de-duplicated. There is no P0
    idempotency layer yet (Redis-backed, ADR-0003), and for a safety channel
    recording a duplicate on a client retry is strictly safer than dropping a
    report — operators de-duplicate during triage. Never lose a safety signal.

    ``upload`` is the structured exception to the "no structured target from a fan"
    rule above, and it is safe for the same reason cast_id is not: an Upload id is a
    server-minted UUID the fan received from our own upload endpoint, not free text —
    it can carry no PII into the ledger, and the API layer resolves it to a real row
    before it reaches here. This is what makes an uploaded image reportable.

    Raises :class:`SafetyReportError` for a type a fan may not self-file.
    """
    if report_type not in FAN_REPORTABLE_TYPES:
        # Generic message — never echo the raw report_type back (a fan could put PII
        # in it and have it reflected through the 422 response).
        raise SafetyReportError("report_type is not fan-reportable.")
    severity = fan_report_severity(report_type)
    report = SafetyReport.objects.create(
        report_type=report_type,
        severity=severity,
        visibility=_visibility_for(severity),
        reporter_type=ActorKind.FAN.value,
        target_type=ActorKind.UNKNOWN.value,
        reporter=reporter,
        upload=upload,
        created_by=reporter,
    )
    SafetyReportDetail.objects.create(report=report, narrative=narrative)
    emit_event(
        event_name=EventName.SAFETY_REPORT_CREATED.value,
        occurred_at=report.created_at,
        actor_type=ActorType.FAN.value,
        source=EventSource.FAN_APP.value,
        actor_id=str(reporter.fan_id),
        fan_id=str(reporter.fan_id),
        actor_is_operator=False,
        ids=_report_ids(report),
        # Classification + visibility + ids only — never the narrative.
        payload={
            "safety_report_id": str(report.id),
            "reporter_type": ActorKind.FAN.value,
            "target_type": ActorKind.UNKNOWN.value,
            "report_type": report_type,
            "severity": severity,
            "visibility": report.visibility,
        },
    )
    return report


def _other_actioned_report_exists(*, upload: Upload, excluding: SafetyReport) -> bool:
    """Whether some report OTHER than ``excluding`` still holds ``upload`` down."""
    return (
        SafetyReport.objects.filter(upload=upload, status=ReportStatus.ACTIONED.value)
        .exclude(id=excluding.id)
        .exists()
    )


@transaction.atomic
def change_report_status(*, report: SafetyReport, status: str, actor: Account) -> SafetyReport:
    """Advance the report's handling status with an audit entry.

    Closing is done via :func:`resolve_report` (which also emits the resolved
    event); this covers the received→reviewing→actioned transitions.

    ``actioned`` is the operator's "this content is not allowed" decision, so when the
    report is bound to an upload this is where that decision takes effect: the image
    is taken down and stops being served (report-driven human moderation, 대표 approved
    07-18). Same transaction as the status change — an ACTIONED report and a still-
    served image must never be observable together.

    Moving such a report *back off* ``actioned`` is the un-action, and it reverses the
    takedown: the image is restored and serves again. That reversal is the whole reason
    a takedown moves the bytes to quarantine instead of deleting them — an operator who
    actioned the wrong report must be able to undo it. Note that closing the report
    (:func:`resolve_report`) is not an un-action: an actioned-then-closed report is the
    normal end state and the image stays down.
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
    upload = report.upload
    if upload is not None:
        if status == ReportStatus.ACTIONED.value:
            take_down_upload(upload=upload, actor=actor, report_id=str(report.id))
        elif before == ReportStatus.ACTIONED.value and not _other_actioned_report_exists(
            upload=upload, excluding=report
        ):
            # Un-action. Only the LAST actioned report holding an image down may
            # restore it: one image can attract several reports, and reverting one
            # operator's call must not silently undo another's.
            restore_upload(upload=upload, actor=actor, report_id=str(report.id))
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
    report.resolved_at = timezone.now()
    report.save(update_fields=["status", "resolved_at", "updated_at"])
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
            AuditAction.USER_RISK_FLAGGED.value if is_risk_flag else AuditAction.USER_BLOCKED.value
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
