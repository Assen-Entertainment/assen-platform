"""Unit tests for the operator dashboard projection (ASS-97 daily_metrics)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import daily_metrics, emit_event
from apps.identity.models import Account, Role
from apps.visit.services import record_visit, void_visit

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def test_daily_metrics_scopes_visits_to_the_day() -> None:
    """Visits are counted in their own day's window, not another day's."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    now = timezone.now()
    record_visit(fan=fan, visited_at=now, actor=operator)
    record_visit(fan=fan, visited_at=now, actor=operator)
    record_visit(fan=fan, visited_at=now - timedelta(days=1), actor=operator)

    today = daily_metrics(day=timezone.localdate())
    yesterday = daily_metrics(day=timezone.localdate() - timedelta(days=1))

    assert today.visits == 2
    assert today.business_day == timezone.localdate().isoformat()
    assert yesterday.visits == 1
    # No other event types emitted → zeroed, proving the projection runs.
    assert today.cheki == 0
    assert today.reservations == 0
    assert today.favorites == 0


def test_daily_metrics_safety_open_is_created_minus_resolved() -> None:
    """The safety backlog gauge is open reports (created not yet resolved)."""
    operator = _account(Role.OPERATOR.value)

    def _safety(event_name: str, report_id: str) -> None:
        payload = {"safety_report_id": report_id}
        if event_name == EventName.SAFETY_REPORT_CREATED.value:
            payload |= {
                "reporter_type": "fan",
                "target_type": "cast",
                "report_type": "harassment",
                "severity": "low",
                "visibility": "restricted",
            }
        else:
            payload |= {"resolution": "actioned"}
        emit_event(
            event_name=event_name,
            occurred_at=timezone.now(),
            actor_type=ActorType.OPERATOR.value,
            source=EventSource.MANUAL.value,
            actor_id=str(operator.fan_id),
            actor_is_operator=True,
            payload=payload,
        )

    _safety(EventName.SAFETY_REPORT_CREATED.value, "r1")
    _safety(EventName.SAFETY_REPORT_CREATED.value, "r2")
    _safety(EventName.SAFETY_REPORT_RESOLVED.value, "r1")

    metrics = daily_metrics(day=timezone.localdate())
    assert metrics.safety_reports_open == 1


def test_daily_metrics_safety_open_never_negative() -> None:
    """A stray resolved-without-created never drives the gauge below zero."""
    operator = _account(Role.OPERATOR.value)
    emit_event(
        event_name=EventName.SAFETY_REPORT_RESOLVED.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_id=str(operator.fan_id),
        actor_is_operator=True,
        payload={"safety_report_id": "r9", "resolution": "actioned"},
    )
    assert daily_metrics(day=timezone.localdate()).safety_reports_open == 0


def test_daily_metrics_visits_are_gross_voids_not_netted() -> None:
    """A same-day void leaves the check-in in the gross dashboard count.

    The dashboard is an at-a-glance operational gauge: a voided visit emits a
    separate ``visit_invalidated`` event but the original ``visit_checked_in``
    stays in the count (unlike the netted MSFC metric). This pins the intentional
    gross behaviour so it is not silently "fixed" into netting later.
    """
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    record = record_visit(fan=fan, visited_at=timezone.now(), actor=operator)
    void_visit(record=record, reason="duplicate scan", actor=operator)

    assert daily_metrics(day=timezone.localdate()).visits == 1


def test_daily_metrics_window_is_half_open_at_midnight() -> None:
    """The day window is ``[00:00, next 00:00)``: the start counts, the end does not."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    today = timezone.localdate()
    start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    next_midnight = start + timedelta(days=1)
    record_visit(fan=fan, visited_at=start, actor=operator)
    record_visit(fan=fan, visited_at=next_midnight, actor=operator)

    # The boundary event belongs to the next day, not today (half-open window).
    assert daily_metrics(day=today).visits == 1
    assert daily_metrics(day=today + timedelta(days=1)).visits == 1
