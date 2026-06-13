"""Operator dashboard API (ASS-97 v0).

A single at-a-glance endpoint: daily counts projected from the event ledger,
plus a usage log on every view so weekly dashboard usage is measurable (the
ASS-97 acceptance criterion). Status-edit entry points, CSV export, and the
admin-only sections (settings/permissions/risk/audit-log) are v1 follow-ups.
"""

from __future__ import annotations

from datetime import date as date_cls
from typing import cast

from django.http import HttpRequest
from django.utils import timezone
from ninja import Router, Schema

from apps.admin_rbac.permissions import operator_required
from apps.audit.models import AuditAction
from apps.audit.services import record_audit
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
def get_dashboard(
    request: HttpRequest, date: date_cls | None = None
) -> DashboardOut:
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
