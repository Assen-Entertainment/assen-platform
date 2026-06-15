"""Operator dashboard API (ASS-97 v0).

A single at-a-glance endpoint: daily counts projected from the event ledger,
plus a usage log on every view so weekly dashboard usage is measurable (the
ASS-97 acceptance criterion). Status-edit entry points, CSV export, and the
admin-only sections (settings/permissions/risk/audit-log) are v1 follow-ups.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date as date_cls
from datetime import datetime
from typing import cast

from django.http import HttpRequest
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.admin_rbac.permissions import operator_required
from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.dashboard.metrics import month_bounds, operator_kpi_metrics
from apps.event_log.services import daily_metrics
from apps.identity.models import Account
from config.api import api

router = Router(auth=operator_required, tags=["operator-dashboard"])


class DashboardOut(Schema):
    """Daily at-a-glance operator metrics (counts only, no personal data)."""

    business_day: str
    visits: int
    cheki: int
    reservations: int
    favorites: int
    safety_reports_open: int


@router.get("/", response=DashboardOut)
def get_dashboard(request: HttpRequest, date: date_cls | None = None) -> DashboardOut:
    """Return the day's dashboard metrics and record the view as usage.

    ``date`` defaults to today (operator's local date). The view is logged to the
    audit trail (``dashboard_viewed``) so weekly usage is countable.
    """
    day = date or timezone.localdate()
    metrics = daily_metrics(day=day)
    record_audit(
        actor=cast(Account, request.auth),  # type: ignore[attr-defined]
        action=AuditAction.DASHBOARD_VIEWED.value,
        # target is the accessed subject (the dashboard); the viewed day is data.
        target="operator_dashboard",
        metadata={"business_day": metrics.business_day},
    )
    return DashboardOut(
        business_day=metrics.business_day,
        visits=metrics.visits,
        cheki=metrics.cheki,
        reservations=metrics.reservations,
        favorites=metrics.favorites,
        safety_reports_open=metrics.safety_reports_open,
    )


api.add_router("/operator/dashboard", router)


metrics_router = Router(auth=operator_required, tags=["operator-metrics"])


class KpiMetricsOut(Schema):
    """MSFC + rate + guardrail KPIs for a period (counts/rates only, no PII).

    Mirrors :class:`apps.dashboard.metrics.OperatorKpiMetrics`. Rates are
    fractions in ``[0, 1]`` (``0.0`` when the denominator is empty);
    ``period_end`` is exclusive.
    """

    period_start: str
    period_end: str
    msfc: int
    verified_visit_fans: int
    safe_fan_continuation_rate: float
    first_visit_fans: int
    thirty_day_return_rate: float
    favorite_registrations: int
    favorite_to_visit_rate: float
    schedule_view_fans: int
    schedule_to_reservation_rate: float
    schedule_to_visit_rate: float
    signups: int
    visitor_signup_rate: float
    favorite_registration_rate: float
    cheki_record_rate: float
    safety_reports_created: int
    safety_report_rate_per_visit: float
    users_blocked: int
    excluded_risk_fans: int


@metrics_router.get("/", response=KpiMetricsOut)
def get_metrics(
    request: HttpRequest,
    start: date_cls | None = None,
    end: date_cls | None = None,
) -> KpiMetricsOut:
    """Return the MSFC/rate/guardrail KPIs for a window and log the view.

    The window is the half-open ``[start, end)``; both default to the current
    calendar month (``start``/``end`` each fall back to the month of whichever
    bound — or today — is given). The view is audited (``dashboard_viewed``,
    target ``operator_metrics``) so weekly KPI usage is countable.
    """
    today = timezone.localdate()
    month_start, month_end = month_bounds(start or end or today)
    period_start = (
        timezone.make_aware(datetime.combine(start, datetime.min.time()))
        if start is not None
        else month_start
    )
    period_end = (
        timezone.make_aware(datetime.combine(end, datetime.min.time()))
        if end is not None
        else month_end
    )
    if period_end <= period_start:
        raise HttpError(422, "end must be after start.")

    metrics = operator_kpi_metrics(period_start=period_start, period_end=period_end)
    record_audit(
        actor=cast(Account, request.auth),  # type: ignore[attr-defined]
        action=AuditAction.DASHBOARD_VIEWED.value,
        target="operator_metrics",
        metadata={
            "period_start": metrics.period_start,
            "period_end": metrics.period_end,
        },
    )
    return KpiMetricsOut(**asdict(metrics))


api.add_router("/operator/metrics", metrics_router)
