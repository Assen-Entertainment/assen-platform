"""Unit + acceptance tests for the MSFC/KPI pipeline (ASS-112 v0).

Seeds the append-only ledger through the sanctioned ``emit_event`` funnel (so
payloads are schema-validated like production) and the safety models (for the
risk-fan exclusion), then asserts the aggregation matches the North Star /
Weekly KPI definitions: the 30-day boundary, every safe-continuation action, the
exclusion rules (operator/invalidated/refunded/blocked/reported), the rate
denominators (incl. 0-guards), and the operator gating on the endpoint.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEntry
from apps.dashboard.metrics import operator_kpi_metrics
from apps.event_log.events import ActorType, EventName, EventSource, EventStatus
from apps.event_log.services import emit_event
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.safety.models import (
    ActorKind,
    BlockScope,
    BlockStatus,
    ReportSeverity,
    ReportStatus,
    ReportType,
    ReportVisibility,
    SafetyReport,
    UserBlock,
)

pytestmark = pytest.mark.django_db

PERIOD_START = timezone.make_aware(datetime(2026, 6, 1))
PERIOD_END = timezone.make_aware(datetime(2026, 7, 1))


def _at(day: int, hour: int = 12) -> datetime:
    """An aware June 2026 timestamp inside the test window."""
    return timezone.make_aware(datetime(2026, 6, day, hour))


def _metrics() -> Any:
    """Run the pipeline over the fixed June 2026 window."""
    return operator_kpi_metrics(period_start=PERIOD_START, period_end=PERIOD_END)


def _visit(
    fan_id: str,
    when: datetime,
    *,
    visit_id: str,
    verified: bool = True,
    operator: bool = False,
    status: str = EventStatus.COMPLETED.value,
    quality: dict[str, bool] | None = None,
) -> None:
    emit_event(
        event_name=EventName.VISIT_CHECKED_IN.value,
        occurred_at=when,
        actor_type=ActorType.OPERATOR.value if operator else ActorType.FAN.value,
        source=EventSource.KIOSK.value,
        fan_id=fan_id,
        visit_id=visit_id,
        actor_is_operator=operator,
        status=status,
        quality=quality,
        payload={
            "visit_id": visit_id,
            "store_id": "store-1",
            "business_day": when.date().isoformat(),
            "visit_type": "store_visit",
            "checkin_method": "qr",
            "is_verified_offline_visit": verified,
        },
    )


def _visit_completed(fan_id: str, when: datetime, *, visit_id: str) -> None:
    emit_event(
        event_name=EventName.VISIT_COMPLETED.value,
        occurred_at=when,
        actor_type=ActorType.FAN.value,
        source=EventSource.KIOSK.value,
        fan_id=fan_id,
        visit_id=visit_id,
        payload={
            "fan_id": fan_id,
            "visit_id": visit_id,
            "completed_at": when.isoformat(),
            "has_payment_reference": True,
        },
    )


def _cancel_reservation(fan_id: str, reservation_id: str) -> None:
    emit_event(
        event_name=EventName.RESERVATION_CANCELLED.value,
        occurred_at=_at(20),
        actor_type=ActorType.FAN.value,
        source=EventSource.FAN_APP.value,
        fan_id=fan_id,
        status=EventStatus.CANCELLED.value,
        payload={"fan_id": fan_id, "reservation_id": reservation_id},
    )


def _favorite(fan_id: str, when: datetime, *, status: str = EventStatus.COMPLETED.value) -> None:
    emit_event(
        event_name=EventName.FAVORITE_ADDED.value,
        occurred_at=when,
        actor_type=ActorType.FAN.value,
        source=EventSource.FAN_APP.value,
        fan_id=fan_id,
        status=status,
        payload={"fan_id": fan_id, "cast_id": "cast-1", "favorite_source": "profile"},
    )


def _cheki(fan_id: str, when: datetime, *, cheki_id: str) -> None:
    emit_event(
        event_name=EventName.CHEKI_RECORDED.value,
        occurred_at=when,
        actor_type=ActorType.FAN.value,
        source=EventSource.FAN_APP.value,
        fan_id=fan_id,
        visit_id="visit-x",
        payload={
            "visit_id": "visit-x",
            "cast_id": "cast-1",
            "cheki_id": cheki_id,
            "cheki_type": "standard",
            "quantity": 1,
            "image_stored": True,
        },
    )


def _event_reserved(
    fan_id: str, when: datetime, *, status: str = EventStatus.COMPLETED.value
) -> None:
    emit_event(
        event_name=EventName.EVENT_RESERVED.value,
        occurred_at=when,
        actor_type=ActorType.FAN.value,
        source=EventSource.FAN_APP.value,
        fan_id=fan_id,
        status=status,
        payload={
            "fan_id": fan_id,
            "event_campaign_id": "camp-1",
            "reservation_id": f"er-{fan_id}",
            "event_type": "birthday",
            "reservation_status": "confirmed",
        },
    )


def _schedule_view(fan_id: str, when: datetime) -> None:
    emit_event(
        event_name=EventName.SCHEDULE_VIEWED.value,
        occurred_at=when,
        actor_type=ActorType.FAN.value,
        source=EventSource.FAN_APP.value,
        fan_id=fan_id,
        payload={
            "store_id": "store-1",
            "business_day": when.date().isoformat(),
            "viewed_for_date": when.date().isoformat(),
            "view_scope": "store",
            "source_surface": "app",
        },
    )


def _reservation(fan_id: str, when: datetime) -> None:
    emit_event(
        event_name=EventName.RESERVATION_CREATED.value,
        occurred_at=when,
        actor_type=ActorType.FAN.value,
        source=EventSource.FAN_APP.value,
        fan_id=fan_id,
        payload={"fan_id": fan_id, "reservation_id": f"res-{fan_id}"},
    )


def _signup(fan_id: str, when: datetime) -> None:
    emit_event(
        event_name=EventName.FAN_SIGNED_UP.value,
        occurred_at=when,
        actor_type=ActorType.FAN.value,
        source=EventSource.FAN_APP.value,
        fan_id=fan_id,
        payload={
            "fan_id": fan_id,
            "signup_method": "qr",
            "consent_terms": True,
            "consent_privacy": True,
        },
    )


def _invalidate_visit(visit_id: str) -> None:
    emit_event(
        event_name=EventName.VISIT_INVALIDATED.value,
        occurred_at=_at(20),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        visit_id=visit_id,
        actor_is_operator=True,
        status=EventStatus.INVALIDATED.value,
        payload={"visit_id": visit_id, "reason": "void"},
    )


def _invalidate_cheki(cheki_id: str) -> None:
    emit_event(
        event_name=EventName.CHEKI_INVALIDATED.value,
        occurred_at=_at(20),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_is_operator=True,
        status=EventStatus.INVALIDATED.value,
        payload={"cheki_id": cheki_id, "reason": "void"},
    )


# --- MSFC core --------------------------------------------------------------


def test_msfc_counts_only_fans_with_a_safe_followup() -> None:
    _visit("fan-a", _at(5), visit_id="va")
    _favorite("fan-a", _at(15))  # +10 days
    _visit("fan-b", _at(5), visit_id="vb")  # no follow-up

    metrics = _metrics()

    assert metrics.verified_visit_fans == 2
    assert metrics.msfc == 1
    assert metrics.safe_fan_continuation_rate == 0.5


def test_msfc_boundary_includes_30_days_excludes_31() -> None:
    _visit("fan-a", _at(1), visit_id="va")
    _favorite("fan-a", _at(1) + timedelta(days=30))  # inclusive
    _visit("fan-b", _at(1), visit_id="vb")
    _favorite("fan-b", _at(1) + timedelta(days=31))  # too late

    metrics = _metrics()

    assert metrics.verified_visit_fans == 2
    assert metrics.msfc == 1


@pytest.mark.parametrize("action", ["favorite", "cheki", "event", "revisit"])
def test_each_safe_followup_type_qualifies(action: str) -> None:
    _visit("fan-a", _at(5), visit_id="va")
    if action == "favorite":
        _favorite("fan-a", _at(10))
    elif action == "cheki":
        _cheki("fan-a", _at(10), cheki_id="ck1")
    elif action == "event":
        _event_reserved("fan-a", _at(10))
    else:
        _visit("fan-a", _at(10), visit_id="va2")  # a distinct later visit

    assert _metrics().msfc == 1


def test_a_visit_does_not_satisfy_itself() -> None:
    # A single check-in with no distinct follow-up is a start, not an MSFC.
    _visit("fan-a", _at(5), visit_id="va")

    metrics = _metrics()

    assert metrics.verified_visit_fans == 1
    assert metrics.msfc == 0


# --- Exclusions -------------------------------------------------------------


def test_operator_visits_are_excluded() -> None:
    _visit("op-fan", _at(5), visit_id="va", operator=True)
    _favorite("op-fan", _at(10))

    metrics = _metrics()

    assert metrics.verified_visit_fans == 0
    assert metrics.msfc == 0


def test_invalidated_visit_is_excluded_as_an_anchor() -> None:
    _visit("fan-a", _at(5), visit_id="va")
    _invalidate_visit("va")
    _favorite("fan-a", _at(10))

    metrics = _metrics()

    assert metrics.verified_visit_fans == 0
    assert metrics.msfc == 0


def test_non_completed_followup_does_not_qualify() -> None:
    _visit("fan-a", _at(5), visit_id="va")
    _event_reserved("fan-a", _at(10), status=EventStatus.CANCELLED.value)

    metrics = _metrics()

    assert metrics.verified_visit_fans == 1
    assert metrics.msfc == 0


def test_invalidated_cheki_does_not_qualify_as_followup() -> None:
    _visit("fan-a", _at(5), visit_id="va")
    _cheki("fan-a", _at(10), cheki_id="ck1")
    _invalidate_cheki("ck1")

    assert _metrics().msfc == 0


def test_unverified_visit_is_not_an_anchor() -> None:
    _visit("fan-a", _at(5), visit_id="va", verified=False)
    _favorite("fan-a", _at(10))

    metrics = _metrics()

    assert metrics.verified_visit_fans == 0
    assert metrics.msfc == 0


def test_visit_completed_qualifies_as_a_revisit() -> None:
    # A 재방문 may be a completion, not only a check-in (North Star 체크인/결제).
    _visit("fan-a", _at(5), visit_id="va")
    _visit_completed("fan-a", _at(12), visit_id="vb")

    assert _metrics().msfc == 1


def test_invalidated_revisit_does_not_qualify() -> None:
    _visit("fan-a", _at(5), visit_id="va")
    _visit("fan-a", _at(12), visit_id="vb")  # a revisit...
    _invalidate_visit("vb")  # ...later voided

    metrics = _metrics()

    assert metrics.verified_visit_fans == 1  # the anchor "va" is still valid
    assert metrics.msfc == 0  # the only follow-up was the voided revisit


def test_cancelled_event_reservation_does_not_qualify() -> None:
    _visit("fan-a", _at(5), visit_id="va")
    _event_reserved("fan-a", _at(10))  # reservation_id == "er-fan-a"
    _cancel_reservation("fan-a", "er-fan-a")

    assert _metrics().msfc == 0


def test_quality_flagged_test_traffic_is_excluded() -> None:
    _visit("fan-a", _at(5), visit_id="va", quality={"is_test": True})
    _favorite("fan-a", _at(10))

    metrics = _metrics()

    assert metrics.verified_visit_fans == 0
    assert metrics.msfc == 0


# --- Risk-fan exclusion (safety models, lift-aware) -------------------------


def _staff() -> Account:
    return Account.objects.create(role=Role.OPERATOR.value)


def _blocked_fan(*, status: str) -> Account:
    fan = Account.objects.create(role=Role.FAN.value)
    UserBlock.objects.create(
        target=fan,
        block_scope=BlockScope.ALL.value,
        block_reason="policy",
        effective_from=_at(1),
        status=status,
        created_by=_staff(),
    )
    return fan


def test_actively_blocked_fan_is_excluded_from_msfc_and_pool() -> None:
    blocked = _blocked_fan(status=BlockStatus.ACTIVE.value)
    _visit(str(blocked.fan_id), _at(5), visit_id="vb")
    _favorite(str(blocked.fan_id), _at(10))
    _visit("fan-ok", _at(5), visit_id="vo")
    _favorite("fan-ok", _at(10))

    metrics = _metrics()

    assert metrics.verified_visit_fans == 1  # only fan-ok
    assert metrics.msfc == 1
    assert metrics.excluded_risk_fans == 1


def test_lifted_block_does_not_exclude_the_fan() -> None:
    lifted = _blocked_fan(status=BlockStatus.LIFTED.value)
    _visit(str(lifted.fan_id), _at(5), visit_id="vb")
    _favorite(str(lifted.fan_id), _at(10))

    metrics = _metrics()

    assert metrics.verified_visit_fans == 1
    assert metrics.msfc == 1
    assert metrics.excluded_risk_fans == 0


def test_open_report_target_is_excluded() -> None:
    fan = Account.objects.create(role=Role.FAN.value)
    SafetyReport.objects.create(
        report_type=ReportType.UNWANTED_REQUEST.value,
        severity=ReportSeverity.LOW.value,
        visibility=ReportVisibility.RESTRICTED.value,
        reporter_type=ActorKind.CAST.value,
        target_type=ActorKind.FAN.value,
        target=fan,
        status=ReportStatus.RECEIVED.value,
        created_by=_staff(),
    )
    _visit(str(fan.fan_id), _at(5), visit_id="vb")
    _favorite(str(fan.fan_id), _at(10))

    metrics = _metrics()

    assert metrics.verified_visit_fans == 0
    assert metrics.excluded_risk_fans == 1


# --- Rates ------------------------------------------------------------------


def test_thirty_day_return_rate() -> None:
    _visit("fan-a", _at(2), visit_id="va1")
    _visit("fan-a", _at(12), visit_id="va2")  # returned within 30d
    _visit("fan-b", _at(2), visit_id="vb1")  # first visit, no return

    metrics = _metrics()

    assert metrics.first_visit_fans == 2
    assert metrics.thirty_day_return_rate == 0.5


def test_schedule_conversion_uses_a_7_day_window() -> None:
    _schedule_view("fan-a", _at(2))
    _reservation("fan-a", _at(8))  # +6 days -> converts
    _schedule_view("fan-b", _at(2))
    _visit("fan-b", _at(2) + timedelta(days=8), visit_id="late")  # +8 days -> no

    metrics = _metrics()

    assert metrics.schedule_view_fans == 2
    assert metrics.schedule_to_reservation_rate == 0.5
    assert metrics.schedule_to_visit_rate == 0.0


def test_activation_rates_use_signup_denominator() -> None:
    _signup("fan-a", _at(2))
    _visit("fan-a", _at(3), visit_id="va")
    _favorite("fan-a", _at(4))
    _cheki("fan-a", _at(5), cheki_id="ck1")
    _signup("fan-b", _at(2))  # signed up, no favorite/cheki

    metrics = _metrics()

    assert metrics.signups == 2
    assert metrics.verified_visit_fans == 1
    assert metrics.visitor_signup_rate == 2.0  # 2 signups / 1 verified visitor
    assert metrics.favorite_registration_rate == 0.5
    assert metrics.cheki_record_rate == 0.5


def test_empty_ledger_rates_are_zero_not_errors() -> None:
    metrics = _metrics()

    assert metrics.msfc == 0
    assert metrics.safe_fan_continuation_rate == 0.0
    assert metrics.thirty_day_return_rate == 0.0
    assert metrics.favorite_to_visit_rate == 0.0
    assert metrics.cheki_record_rate == 0.0


# --- Guardrails -------------------------------------------------------------


def test_guardrail_counts_reports_and_blocks() -> None:
    _visit("fan-a", _at(5), visit_id="va")
    _visit("fan-b", _at(6), visit_id="vb")
    emit_event(
        event_name=EventName.SAFETY_REPORT_CREATED.value,
        occurred_at=_at(7),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_is_operator=True,
        payload={
            "safety_report_id": "r1",
            "reporter_type": "cast",
            "target_type": "fan",
            "report_type": "unwanted_request",
            "severity": "low",
            "visibility": "restricted",
        },
    )
    emit_event(
        event_name=EventName.USER_BLOCKED.value,
        occurred_at=_at(8),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_is_operator=True,
        payload={
            "block_id": "b1",
            "block_scope": "all",
            "block_reason": "policy_violation",
            "effective_from": _at(8).isoformat(),
        },
    )

    metrics = _metrics()

    assert metrics.safety_reports_created == 1
    assert metrics.users_blocked == 1
    assert metrics.safety_report_rate_per_visit == 0.5  # 1 report / 2 visits


def test_window_scopes_out_other_months() -> None:
    _visit("fan-a", timezone.make_aware(datetime(2026, 5, 30)), visit_id="may")
    _favorite("fan-a", timezone.make_aware(datetime(2026, 6, 2)))

    metrics = _metrics()  # June window

    assert metrics.verified_visit_fans == 0  # the May visit is out of window


def test_msfc_counts_followup_after_period_end_within_30d() -> None:
    # Anchor late in the window; the safe follow-up lands the next month but
    # within 30 days -> still MSFC (the horizon extends past period_end).
    _visit("fan-a", _at(28), visit_id="va")
    _favorite("fan-a", timezone.make_aware(datetime(2026, 7, 5)))

    metrics = _metrics()

    assert metrics.verified_visit_fans == 1
    assert metrics.msfc == 1


def test_risk_exclusion_is_scoped_to_msfc_not_other_pools() -> None:
    blocked = _blocked_fan(status=BlockStatus.ACTIVE.value)
    fid = str(blocked.fan_id)
    _signup(fid, _at(2))
    _visit(fid, _at(3), visit_id="vb")

    metrics = _metrics()

    # Excluded from the MSFC pool...
    assert metrics.verified_visit_fans == 0
    assert metrics.excluded_risk_fans == 1
    # ...but still counted in the non-MSFC activation / return pools.
    assert metrics.signups == 1
    assert metrics.first_visit_fans == 1


def test_safety_report_rate_excludes_operator_visits_from_denominator() -> None:
    _visit("fan-a", _at(5), visit_id="va")
    _visit("op", _at(5), visit_id="vop", operator=True)  # must not inflate denom
    emit_event(
        event_name=EventName.SAFETY_REPORT_CREATED.value,
        occurred_at=_at(6),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_is_operator=True,
        payload={
            "safety_report_id": "r1",
            "reporter_type": "cast",
            "target_type": "fan",
            "report_type": "unwanted_request",
            "severity": "low",
            "visibility": "restricted",
        },
    )

    metrics = _metrics()

    assert metrics.safety_reports_created == 1
    assert metrics.safety_report_rate_per_visit == 1.0  # 1 report / 1 fan visit


def test_safety_report_rate_excludes_voided_visits_from_denominator() -> None:
    _visit("fan-a", _at(5), visit_id="va")  # valid
    _visit("fan-b", _at(5), visit_id="vb")
    _invalidate_visit("vb")  # voided -> not in the denominator
    emit_event(
        event_name=EventName.SAFETY_REPORT_CREATED.value,
        occurred_at=_at(6),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_is_operator=True,
        payload={
            "safety_report_id": "r1",
            "reporter_type": "cast",
            "target_type": "fan",
            "report_type": "unwanted_request",
            "severity": "low",
            "visibility": "restricted",
        },
    )

    metrics = _metrics()

    assert metrics.safety_reports_created == 1
    assert metrics.safety_report_rate_per_visit == 1.0  # 1 report / 1 valid visit


# --- API --------------------------------------------------------------------


def _auth(account: Account) -> dict[str, str]:
    token = issue_token_pair(account).access_token
    return {"authorization": f"Bearer {token}"}


def test_metrics_endpoint_returns_kpis_and_logs_usage(client: Client) -> None:
    operator = Account.objects.create(role=Role.OPERATOR.value)
    today = timezone.localdate()
    _visit("fan-a", timezone.now(), visit_id="va")
    _favorite("fan-a", timezone.now())

    response = client.get(
        "/api/operator/metrics/",
        data={"start": today.replace(day=1).isoformat()},
        headers=_auth(operator),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verified_visit_fans"] == 1
    assert body["msfc"] == 1
    assert body["safe_fan_continuation_rate"] == 1.0
    assert "schedule_to_visit_rate" in body
    assert AuditEntry.objects.filter(
        action=AuditAction.DASHBOARD_VIEWED.value,
        actor=operator,
        target="operator_metrics",
    ).exists()


def test_metrics_endpoint_is_operator_gated(client: Client) -> None:
    fan = Account.objects.create(role=Role.FAN.value)
    response = client.get("/api/operator/metrics/", headers=_auth(fan))
    assert response.status_code in {401, 403}


def test_metrics_endpoint_rejects_inverted_window(client: Client) -> None:
    operator = Account.objects.create(role=Role.OPERATOR.value)
    response = client.get(
        "/api/operator/metrics/",
        data={"start": "2026-06-10", "end": "2026-06-01"},
        headers=_auth(operator),
    )
    assert response.status_code == 422
