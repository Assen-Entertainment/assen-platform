"""Safety report-handling operations metrics for the operator queue (ASS-111).

ASS-96 built the report lifecycle (file → status → resolve); this adds the
"처리 시간 집계" the F11 completion calls for: how the open queue is distributed and
how quickly resolved reports were handled. It reads the :class:`SafetyReport`
rows — the source of truth for status — not the event ledger: status is mutable
model state with no per-transition corrective event, so the rows (like the
dashboard's risk-fan join) are the accurate source.

Counts + durations (seconds) only; the narrative/PII never leaves the restricted
:class:`~apps.safety.models.SafetyReportDetail`. Determinism: figures are read as
of an explicit ``as_of`` instant with an explicit ``window`` for the throughput
leg, so results are reproducible from seeded rows with no hidden clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

from apps.safety.models import ReportSeverity, ReportStatus, SafetyReport


@dataclass(frozen=True)
class ReportHandlingStats:
    """Triage-queue health for one ``as_of`` + trailing ``window`` (counts/seconds)."""

    window_days: int
    as_of: str
    # Open queue (status != closed) — current row state.
    open_total: int
    open_received: int
    open_reviewing: int
    open_actioned: int
    open_low: int
    open_medium: int
    open_high: int
    open_critical: int
    oldest_open_age_seconds: int
    # Throughput over the trailing half-open window [as_of - window, as_of).
    resolved_in_window: int
    median_handling_seconds: int
    avg_handling_seconds: int


def report_handling_stats(*, as_of: datetime, window: timedelta) -> ReportHandlingStats:
    """Project report-handling metrics as of ``as_of`` over a trailing ``window``.

    Open-queue figures reflect current row state (a report is open while its
    status is not ``closed``); ``as_of`` anchors the age and the resolved-window
    bounds. Handling time is ``resolved_at - created_at`` for reports resolved in
    the half-open ``[as_of - window, as_of)`` (matching the dashboard's window
    convention); a report closed before ``resolved_at`` existed has a NULL and is
    excluded (none exist in a fresh store).
    """
    window_start = as_of - window

    open_counts = {
        status: 0 for status in ReportStatus.values if status != ReportStatus.CLOSED.value
    }
    severity_counts = {severity: 0 for severity in ReportSeverity.values}
    open_total = 0
    oldest_open_age = 0
    open_rows = SafetyReport.objects.exclude(status=ReportStatus.CLOSED.value).values_list(
        "status", "severity", "created_at"
    )
    for status, severity, created_at in open_rows:
        # open_total counts every non-closed row; the status buckets cover the
        # known open statuses. They coincide today and would only diverge if a new
        # open status were added — open_total stays the faithful total either way.
        open_total += 1
        if status in open_counts:
            open_counts[status] += 1
        if severity in severity_counts:
            severity_counts[severity] += 1
        # Clamp: a backdated / future-dated row must never yield a negative age
        # (the response advertises non-negative seconds).
        age = max(0, int((as_of - created_at).total_seconds()))
        oldest_open_age = max(oldest_open_age, age)

    durations = [
        max(0, int((resolved_at - created_at).total_seconds()))
        for created_at, resolved_at in SafetyReport.objects.filter(
            status=ReportStatus.CLOSED.value,
            resolved_at__gte=window_start,
            resolved_at__lt=as_of,
        ).values_list("created_at", "resolved_at")
        if resolved_at is not None
    ]

    return ReportHandlingStats(
        window_days=window.days,
        as_of=as_of.isoformat(),
        open_total=open_total,
        open_received=open_counts.get(ReportStatus.RECEIVED.value, 0),
        open_reviewing=open_counts.get(ReportStatus.REVIEWING.value, 0),
        open_actioned=open_counts.get(ReportStatus.ACTIONED.value, 0),
        open_low=severity_counts.get(ReportSeverity.LOW.value, 0),
        open_medium=severity_counts.get(ReportSeverity.MEDIUM.value, 0),
        open_high=severity_counts.get(ReportSeverity.HIGH.value, 0),
        open_critical=severity_counts.get(ReportSeverity.CRITICAL.value, 0),
        oldest_open_age_seconds=oldest_open_age,
        resolved_in_window=len(durations),
        median_handling_seconds=int(median(durations)) if durations else 0,
        avg_handling_seconds=int(sum(durations) / len(durations)) if durations else 0,
    )
