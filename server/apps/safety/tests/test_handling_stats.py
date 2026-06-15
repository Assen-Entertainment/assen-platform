"""Tests for the safety report-handling metrics + endpoint (ASS-111).

Covers the "처리 시간 집계" completion on top of the ASS-96 lifecycle: open-queue
distribution by status/severity, oldest-open age, resolved-in-window throughput +
handling time, and the operator-gated endpoint. Counts/durations only — the
narrative isolation is asserted by the existing ASS-96/110 suites.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.safety.metrics import ReportHandlingStats, report_handling_stats
from apps.safety.models import ReportStatus, SafetyReport
from apps.safety.services import change_report_status, file_report, resolve_report

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _open_report(operator: Account, *, severity: str, status: str | None = None) -> SafetyReport:
    """File a report and (optionally) advance it to a non-received open status."""
    report = file_report(
        report_type="other",
        severity=severity,
        reporter_type="fan",
        target_type="fan",
        narrative="n",
        actor=operator,
    )
    if status is not None and status != ReportStatus.RECEIVED.value:
        change_report_status(report=report, status=status, actor=operator)
    return report


def _stats(window_days: int = 30) -> ReportHandlingStats:
    """Project handling stats as of now over a trailing window."""
    return report_handling_stats(as_of=timezone.now(), window=timedelta(days=window_days))


# --- metrics ----------------------------------------------------------------


def test_open_queue_counts_by_status_and_severity() -> None:
    """Open reports are bucketed by both status and severity."""
    op = _account(Role.OPERATOR.value)
    _open_report(op, severity="low")
    _open_report(op, severity="high", status=ReportStatus.REVIEWING.value)
    _open_report(op, severity="critical", status=ReportStatus.ACTIONED.value)

    stats = _stats()
    assert stats.open_total == 3
    assert (stats.open_received, stats.open_reviewing, stats.open_actioned) == (1, 1, 1)
    assert (stats.open_low, stats.open_medium, stats.open_high, stats.open_critical) == (1, 0, 1, 1)


def test_closed_report_leaves_the_open_queue_and_counts_as_resolved() -> None:
    """Resolving removes a report from the open queue and adds it to throughput."""
    op = _account(Role.OPERATOR.value)
    mgr = _account(Role.MANAGER.value)
    report = _open_report(op, severity="medium")
    resolve_report(report=report, resolution="ok", resolution_note="", actor=mgr)

    stats = _stats()
    assert stats.open_total == 0
    assert stats.open_medium == 0
    assert stats.resolved_in_window == 1


def test_resolved_at_is_set_only_on_close() -> None:
    """``resolved_at`` is NULL while open and stamped at resolution."""
    op = _account(Role.OPERATOR.value)
    mgr = _account(Role.MANAGER.value)
    report = _open_report(op, severity="low")
    assert report.resolved_at is None

    resolve_report(report=report, resolution="ok", resolution_note="", actor=mgr)
    report.refresh_from_db()
    assert report.resolved_at is not None


def test_handling_time_reflects_created_to_resolved_gap() -> None:
    """Median/mean handling time is the created→resolved gap of resolved reports."""
    op = _account(Role.OPERATOR.value)
    mgr = _account(Role.MANAGER.value)
    report = _open_report(op, severity="low")
    # Backdate creation 2h so the handling time is a known, non-trivial gap.
    SafetyReport.objects.filter(id=report.id).update(created_at=timezone.now() - timedelta(hours=2))
    report.refresh_from_db()
    resolve_report(report=report, resolution="ok", resolution_note="", actor=mgr)

    stats = _stats()
    assert stats.resolved_in_window == 1
    assert 7000 <= stats.median_handling_seconds <= 7400
    assert 7000 <= stats.avg_handling_seconds <= 7400


def test_resolution_outside_the_window_is_excluded_from_throughput() -> None:
    """A report resolved before the window opened is not counted in throughput."""
    op = _account(Role.OPERATOR.value)
    mgr = _account(Role.MANAGER.value)
    report = _open_report(op, severity="low")
    resolve_report(report=report, resolution="ok", resolution_note="", actor=mgr)
    SafetyReport.objects.filter(id=report.id).update(
        resolved_at=timezone.now() - timedelta(days=60)
    )

    stats = _stats(window_days=30)
    assert stats.resolved_in_window == 0


def test_oldest_open_age_tracks_the_earliest_created_open_report() -> None:
    """``oldest_open_age_seconds`` follows the longest-waiting open report."""
    op = _account(Role.OPERATOR.value)
    old = _open_report(op, severity="low")
    SafetyReport.objects.filter(id=old.id).update(created_at=timezone.now() - timedelta(days=3))
    _open_report(op, severity="low")  # fresh

    stats = _stats()
    assert stats.oldest_open_age_seconds >= 3 * 24 * 3600 - 120


def test_empty_store_is_all_zero() -> None:
    """With no reports every figure is zero (no divide-by-zero / no None)."""
    stats = _stats()
    assert stats.open_total == 0
    assert stats.resolved_in_window == 0
    assert stats.oldest_open_age_seconds == 0
    assert stats.median_handling_seconds == 0
    assert stats.avg_handling_seconds == 0


# --- endpoint ---------------------------------------------------------------


def test_handling_stats_endpoint_serves_operator(client: Client) -> None:
    """An operator gets the aggregate with counts-only keys (no PII shapes)."""
    op = _account(Role.OPERATOR.value)
    _open_report(op, severity="high", status=ReportStatus.REVIEWING.value)

    res = client.get("/api/safety/handling-stats", headers=_auth(op))
    assert res.status_code == 200
    body = res.json()
    assert body["open_total"] == 1
    assert body["open_high"] == 1
    assert body["open_reviewing"] == 1
    for key in body:
        assert not any(token in key for token in ("name", "narrative", "phone", "price"))


def test_handling_stats_rejects_fan_and_anonymous(client: Client) -> None:
    """The endpoint is operator-gated: a fan token and no token are refused."""
    fan = _account(Role.FAN.value)
    assert client.get("/api/safety/handling-stats", headers=_auth(fan)).status_code in {401, 403}
    assert client.get("/api/safety/handling-stats").status_code in {401, 403}


def test_handling_stats_validates_window(client: Client) -> None:
    """``window_days`` out of the 1..365 range is rejected (422)."""
    op = _account(Role.OPERATOR.value)
    res_zero = client.get("/api/safety/handling-stats?window_days=0", headers=_auth(op))
    assert res_zero.status_code == 422
    res_big = client.get("/api/safety/handling-stats?window_days=9999", headers=_auth(op))
    assert res_big.status_code == 422
