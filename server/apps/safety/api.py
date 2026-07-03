"""Operator/manager API for safety reports and user blocks (ASS-96).

Two-tier access (admin_rbac):
- **operator+** may file a report, list/triage summaries, and advance status.
  Detail fields are redacted in their responses (``admin_rbac.redaction``).
- **manager+** may read the restricted narrative (audited), resolve a report,
  and block / lift a user.

The narrative never appears in an operator response or any event; it is only
returned by the manager-only detail endpoint, which writes a
``SAFETY_DETAIL_VIEWED`` audit entry on every read.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import cast

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import manager_required, operator_required
from apps.admin_rbac.redaction import redact_safety_report, redact_safety_report_list
from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.identity.auth import fan_auth
from apps.identity.models import Account, Role
from apps.safety.metrics import report_handling_stats
from apps.safety.models import (
    ActorKind,
    BlockReason,
    BlockScope,
    ReportSeverity,
    ReportStatus,
    ReportType,
    SafetyReport,
    UserBlock,
)
from apps.safety.services import (
    SafetyReportError,
    block_user,
    change_report_status,
    file_fan_report,
    file_report,
    lift_block,
    resolve_report,
)
from config.api import api
from config.throttle import user_write_throttle

router = Router(tags=["safety"])

_TEXT_MAX = 2000


class SafetyError(Schema):
    """Stable error shape for safety endpoints."""

    detail: str


class ReportSummaryOut(Schema):
    """Operator-facing report row; detail fields are redacted for non-managers.

    All detail fields are typed ``str`` because the redaction transform may
    replace them with the ``[redacted]`` sentinel.
    """

    safety_report_id: str
    report_type: str
    severity: str
    status: str
    visibility: str
    created_at: datetime
    detail_ref: str
    reporter_id: str
    target_id: str


class ReportDetailOut(Schema):
    """Manager-only restricted detail (narrative + notes)."""

    safety_report_id: str
    narrative: str
    resolution_note: str
    manager_note: str
    reporter_id: str
    target_id: str


class ReportCreateIn(Schema):
    """Operator report intake payload."""

    report_type: str
    severity: str
    reporter_type: str
    target_type: str
    narrative: str = Field(default="", max_length=_TEXT_MAX)
    reporter_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None
    cast_id: str = Field(default="", max_length=64)
    visit_id: uuid.UUID | None = None


class ReportStatusIn(Schema):
    """Status transition (received→reviewing→actioned)."""

    status: str


class ReportResolveIn(Schema):
    """Resolution: a short classification + a restricted-store note."""

    resolution: str = Field(max_length=64)
    resolution_note: str = Field(default="", max_length=_TEXT_MAX)


class BlockCreateIn(Schema):
    """Block/risk-flag intake (manager+)."""

    target_id: uuid.UUID
    block_scope: str
    block_reason: str = Field(max_length=255)
    is_risk_flag: bool = False
    source_report_id: uuid.UUID | None = None


class BlockOut(Schema):
    """Block row exposed to managers."""

    id: uuid.UUID
    target_id: uuid.UUID
    block_scope: str
    block_reason: str
    is_risk_flag: bool
    status: str
    effective_from: datetime


class BlockLiftIn(Schema):
    """Reason required to lift a block."""

    reason: str = Field(max_length=_TEXT_MAX)


class FanReportCreateIn(Schema):
    """Fan self-report intake (ASS-110): a report type plus free-text narrative.

    Only the report type and narrative are accepted. The server fixes everything
    an attacker should not control — the reporter is the authenticated fan,
    ``reporter_type`` is ``fan``, and severity is derived from the type (a fan
    cannot self-assign critical, nor downgrade a threat). A structured ``cast_id``
    is intentionally NOT accepted on the fan surface: it would be untrusted free
    text riding into the append-only event log (a PII channel that bypasses the
    narrative-only restricted store). The fan names the cast in the narrative; an
    operator links the structured cast id during triage.

    ``report_type`` is length-bounded so an oversized value is rejected by schema
    validation (never echoed); the unknown-type error is generic, so a fan cannot
    smuggle PII into ``report_type`` and have it reflected back in a 422.
    """

    report_type: str = Field(max_length=64)
    narrative: str = Field(default="", max_length=_TEXT_MAX)


class FanReportOut(Schema):
    """Receipt returned to the fan: confirmation only, no internal classification.

    Severity/visibility/narrative are operator-internal (Refusal_Report_Block_
    Protocol "자세한 내부 기록은 공개하지 않는다") and are deliberately omitted.
    """

    safety_report_id: str
    status: str
    created_at: datetime


class ReportHandlingStatsOut(Schema):
    """Operator triage-queue health: open distribution + recent handling time.

    Mirrors :class:`apps.safety.metrics.ReportHandlingStats`. Counts and durations
    (seconds) only — no narrative, names, or PII.
    """

    window_days: int
    as_of: str
    open_total: int
    open_received: int
    open_reviewing: int
    open_actioned: int
    open_low: int
    open_medium: int
    open_high: int
    open_critical: int
    oldest_open_age_seconds: int
    resolved_in_window: int
    median_handling_seconds: int
    avg_handling_seconds: int


def _fan_id_or_blank(account: Account | None) -> str:
    """Return the account's public fan_id as a string, or "" when absent."""
    return str(account.fan_id) if account is not None else ""


def _summary_dict(report: SafetyReport) -> dict[str, object]:
    """Build the pre-redaction summary dict (detail_ref points at the store)."""
    return {
        "safety_report_id": str(report.id),
        "report_type": report.report_type,
        "severity": report.severity,
        "status": report.status,
        "visibility": report.visibility,
        "created_at": report.created_at,
        "detail_ref": str(report.id),
        "reporter_id": _fan_id_or_blank(report.reporter),
        "target_id": _fan_id_or_blank(report.target),
    }


@router.post(
    "/reports",
    auth=operator_required,
    response={201: ReportSummaryOut, 400: SafetyError, 404: SafetyError},
)
def create_report(
    request: HttpRequest,
    payload: ReportCreateIn,
) -> tuple[int, dict[str, object] | SafetyError]:
    """File a safety report (operator+); narrative goes to the restricted store."""
    if payload.report_type not in ReportType.values:
        return 400, SafetyError(detail=f"Unknown report_type '{payload.report_type}'.")
    if payload.severity not in ReportSeverity.values:
        return 400, SafetyError(detail=f"Unknown severity '{payload.severity}'.")
    if payload.reporter_type not in ActorKind.values:
        return 400, SafetyError(detail=f"Unknown reporter_type '{payload.reporter_type}'.")
    if payload.target_type not in ActorKind.values:
        return 400, SafetyError(detail=f"Unknown target_type '{payload.target_type}'.")
    reporter = _account_or_none(payload.reporter_id)
    target = _account_or_none(payload.target_id)
    actor = _actor(request)
    report = file_report(
        report_type=payload.report_type,
        severity=payload.severity,
        reporter_type=payload.reporter_type,
        target_type=payload.target_type,
        narrative=payload.narrative,
        actor=actor,
        reporter=reporter,
        target=target,
        cast_id=payload.cast_id,
        visit_id=str(payload.visit_id) if payload.visit_id else "",
    )
    return 201, redact_safety_report(_summary_dict(report), viewer=actor)


@router.post(
    "/fan-reports",
    auth=fan_auth,
    throttle=user_write_throttle("10/min"),
    response={201: FanReportOut, 403: SafetyError, 422: SafetyError},
)
def create_fan_report(
    request: HttpRequest,
    payload: FanReportCreateIn,
) -> tuple[int, FanReportOut | SafetyError]:
    """File a safety report as the authenticated fan (ASS-110, F11; B3).

    **Both surfaces (B3).** Now accepts either the app bearer token or the web
    httpOnly access cookie via :data:`~apps.identity.auth.fan_auth`. The cookie
    surface is CSRF-prone on this state-changing POST, but the grace condition
    ASS-98 attached to enabling it is now met: :data:`fan_auth`'s
    :class:`~apps.identity.auth.FanCookieAuth` enforces Django's double-submit CSRF
    on unsafe methods, so a web caller must echo the ``/fan/csrf`` cookie in
    ``X-CSRFToken`` (the app/bearer surface is not browser-auto-sent and stays
    exempt). Per-user rate-limited (``user_write_throttle``) like the other fan
    writes. The endpoint issues no tokens, so it stays an ordinary business
    endpoint, not auth code.

    The fan is recorded as the reporter, severity is server-derived from the type,
    and the narrative goes only to the restricted store.
    """
    fan = _fan_account(request)
    # FanBearerAuth proves token ownership but is role-agnostic; require the FAN
    # role so a staff token cannot file a report that is then stamped as a fan
    # self-report (reporter_type=fan / actor_is_operator=False would misclassify
    # operator traffic). Mirrors the QR check-in fan gate (apps/visit/checkin_api.py).
    if fan.role != Role.FAN.value:
        return 403, SafetyError(detail="Only fans can file a self-report.")
    try:
        report = file_fan_report(
            reporter=fan,
            report_type=payload.report_type,
            narrative=payload.narrative,
        )
    except SafetyReportError as exc:
        return 422, SafetyError(detail=str(exc))
    return 201, FanReportOut(
        safety_report_id=str(report.id),
        status=report.status,
        created_at=report.created_at,
    )


@router.get(
    "/reports",
    auth=operator_required,
    response={200: list[ReportSummaryOut], 400: SafetyError},
)
def list_reports(
    request: HttpRequest,
    status: str | None = None,
    limit: int = 200,
) -> tuple[int, list[dict[str, object]] | SafetyError]:
    """List report summaries (operator+), each field-redacted for the viewer.

    Bounded by ``limit`` (default 200) so the always-growing safety table cannot
    return an unbounded response.
    """
    if status is not None and status not in ReportStatus.values:
        return 400, SafetyError(detail=f"Unknown status '{status}'.")
    qs = SafetyReport.objects.select_related("reporter", "target")
    if status:
        qs = qs.filter(status=status)
    capped = max(1, min(limit, 500))
    rows = [_summary_dict(report) for report in qs[:capped]]
    return 200, redact_safety_report_list(rows, viewer=_actor(request))


@router.get(
    "/handling-stats",
    auth=operator_required,
    response={200: ReportHandlingStatsOut, 422: SafetyError},
)
def get_handling_stats(
    request: HttpRequest,
    window_days: int = 30,
) -> tuple[int, ReportHandlingStatsOut | SafetyError]:
    """Report-handling operations metrics for the operator triage queue (ASS-111).

    Completes the "신고 ... 처리 시간 집계" workflow on top of the ASS-96 lifecycle:
    the open queue by status/severity, the oldest unresolved age, and how many
    reports were resolved in the trailing ``window_days`` with their median/mean
    handling time. Counts + durations only — never narrative or PII. Operator+,
    matching the report list (these are triage figures, not restricted detail).
    """
    del request  # auth only (operator+); no per-report row is read here.
    if not 1 <= window_days <= 365:
        return 422, SafetyError(detail="window_days must be between 1 and 365.")
    stats = report_handling_stats(as_of=timezone.now(), window=timedelta(days=window_days))
    return 200, ReportHandlingStatsOut(**asdict(stats))


@router.patch(
    "/reports/{report_id}/status",
    auth=operator_required,
    response={200: ReportSummaryOut, 400: SafetyError, 404: SafetyError},
)
def patch_report_status(
    request: HttpRequest,
    report_id: uuid.UUID,
    payload: ReportStatusIn,
) -> tuple[int, dict[str, object] | SafetyError]:
    """Advance a report's handling status (operator+)."""
    if payload.status not in ReportStatus.values:
        return 400, SafetyError(detail=f"Unknown status '{payload.status}'.")
    report = get_object_or_404(SafetyReport, id=report_id)
    actor = _actor(request)
    try:
        change_report_status(report=report, status=payload.status, actor=actor)
    except ValueError as exc:
        return 400, SafetyError(detail=str(exc))
    return 200, redact_safety_report(_summary_dict(report), viewer=actor)


@router.get(
    "/reports/{report_id}/detail",
    auth=manager_required,
    response={200: ReportDetailOut, 400: SafetyError, 404: SafetyError},
)
def get_report_detail(
    request: HttpRequest,
    report_id: uuid.UUID,
    reason: str,
) -> tuple[int, ReportDetailOut | SafetyError]:
    """Read the restricted narrative (manager+ only).

    A non-empty ``reason`` is mandatory and recorded on the SAFETY_DETAIL_VIEWED
    audit entry: access to the platform's most sensitive data must answer "why"
    (audit model compliance contract).
    """
    if not reason.strip():
        return 400, SafetyError(detail="A reason is required to view report detail.")
    report = get_object_or_404(
        SafetyReport.objects.select_related("detail", "reporter", "target"),
        id=report_id,
    )
    actor = _actor(request)
    record_audit(
        actor=actor,
        action=AuditAction.SAFETY_DETAIL_VIEWED.value,
        target=str(report.id),
        reason=reason.strip(),
    )
    detail = report.detail
    return 200, ReportDetailOut(
        safety_report_id=str(report.id),
        narrative=detail.narrative,
        resolution_note=detail.resolution_note,
        manager_note=detail.manager_note,
        reporter_id=_fan_id_or_blank(report.reporter),
        target_id=_fan_id_or_blank(report.target),
    )


@router.post(
    "/reports/{report_id}/resolve",
    auth=manager_required,
    response={200: ReportSummaryOut, 400: SafetyError, 404: SafetyError},
)
def resolve_report_endpoint(
    request: HttpRequest,
    report_id: uuid.UUID,
    payload: ReportResolveIn,
) -> tuple[int, dict[str, object] | SafetyError]:
    """Close a report (manager+); the note lands in the restricted store."""
    report = get_object_or_404(SafetyReport, id=report_id)
    actor = _actor(request)
    try:
        resolve_report(
            report=report,
            resolution=payload.resolution,
            resolution_note=payload.resolution_note,
            actor=actor,
        )
    except ValueError as exc:
        return 400, SafetyError(detail=str(exc))
    return 200, redact_safety_report(_summary_dict(report), viewer=actor)


@router.post(
    "/blocks",
    auth=manager_required,
    response={201: BlockOut, 400: SafetyError, 404: SafetyError},
)
def create_block(
    request: HttpRequest,
    payload: BlockCreateIn,
) -> tuple[int, BlockOut | SafetyError]:
    """Block or risk-flag a fan (manager+)."""
    if payload.block_scope not in BlockScope.values:
        return 400, SafetyError(detail=f"Unknown block_scope '{payload.block_scope}'.")
    if payload.block_reason not in BlockReason.values:
        # Closed reason codes only — a free string could leak PII into the event.
        return 400, SafetyError(detail=f"Unknown block_reason '{payload.block_reason}'.")
    target = get_object_or_404(Account, fan_id=payload.target_id)
    source_report = None
    if payload.source_report_id is not None:
        source_report = get_object_or_404(SafetyReport, id=payload.source_report_id)
    block = block_user(
        target=target,
        block_scope=payload.block_scope,
        block_reason=payload.block_reason,
        effective_from=timezone.now(),
        actor=_actor(request),
        is_risk_flag=payload.is_risk_flag,
        source_report=source_report,
    )
    return 201, _block_out(block)


@router.post(
    "/blocks/{block_id}/lift",
    auth=manager_required,
    response={200: BlockOut, 400: SafetyError, 404: SafetyError},
)
def lift_block_endpoint(
    request: HttpRequest,
    block_id: uuid.UUID,
    payload: BlockLiftIn,
) -> tuple[int, BlockOut | SafetyError]:
    """Lift an active block (manager+) with a mandatory reason."""
    block = get_object_or_404(UserBlock, id=block_id)
    try:
        lift_block(block=block, reason=payload.reason, actor=_actor(request))
    except ValueError as exc:
        return 400, SafetyError(detail=str(exc))
    return 200, _block_out(block)


def _account_or_none(fan_id: uuid.UUID | None) -> Account | None:
    """Resolve an optional fan_id to an Account (None when absent/unknown)."""
    if fan_id is None:
        return None
    return Account.objects.filter(fan_id=fan_id).first()


def _block_out(block: UserBlock) -> BlockOut:
    """Serialise a block for manager responses."""
    return BlockOut(
        id=block.id,
        target_id=block.target.fan_id,
        block_scope=block.block_scope,
        block_reason=block.block_reason,
        is_risk_flag=block.is_risk_flag,
        status=block.status,
        effective_from=block.effective_from,
    )


def _actor(request: HttpRequest) -> Account:
    """Return the authenticated staff account supplied by RoleRequired."""
    # request.auth is untyped without Ninja stubs (same idiom as identity/auth.py).
    return cast(Account, request.auth)  # type: ignore[attr-defined]


def _fan_account(request: HttpRequest) -> Account:
    """Return the authenticated fan account supplied by ``fan_auth``."""
    # request.auth is the Account resolved by FanBearerAuth/FanCookieAuth; untyped
    # without Ninja stubs (same idiom as _actor / identity.api).
    return cast(Account, request.auth)  # type: ignore[attr-defined]


api.add_router("/safety", router)
