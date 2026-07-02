"""MSFC + KPI aggregation pipeline projected from the event ledger (ASS-112 v0).

This is the data foundation for the North Star (``Monthly Safe Fan
Continuations``) and the rate/guardrail KPIs defined in Company-OS
``00_Company_OS/North_Star_Metric.md`` and
``20_Operations/Weekly_KPI_Dashboard_Template.md``. Field names and formulas
mirror those documents 1:1 so the operator surface and the weekly review speak
the same language.

Why this lives in ``dashboard`` (not ``event_log``): the full MSFC must exclude
"위험 고객" — fans with an *active* block or an open report. Block lifting is a
status change on :class:`~apps.safety.models.UserBlock` with **no** corrective
event, so a ledger-only read would over-exclude a fan whose block was lifted.
The accurate source is the safety models, and ``apps.safety`` already imports
``apps.event_log`` — putting this here (a read-projection app above both) keeps
``event_log`` ledger-pure and avoids a dependency cycle.

Determinism: every function is windowed by explicit half-open ``[start, end)``
arguments and reads only persisted rows, so results are reproducible from seeded
data with no hidden clock. The per-fan follow-up scan is O(events) in Python
(test/early-operation scale); the indexed ``(event_name, occurred_at)`` and
``(fan_id)`` columns make the queries cheap, and a set-based SQL rewrite is the
v1 optimisation target as the ledger grows (mirrors ``daily_metrics``).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date as date_cls
from datetime import datetime, timedelta

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.event_log.events import EventName, EventStatus
from apps.event_log.models import EventRecord
from apps.safety.models import ActorKind, BlockStatus, ReportStatus, SafetyReport, UserBlock

# The safe-continuation horizon (North Star: "30일 안에 ... 후속 행동").
MSFC_WINDOW = timedelta(days=30)
# The schedule-view conversion horizon (Weekly_KPI: "조회 후 7일 내").
SCHEDULE_CONVERSION_WINDOW = timedelta(days=7)

# P0 safe-continuation actions available in the event registry. A 재방문 counts
# as either a later check-in OR a completion (North Star "체크인 또는 결제 기준"),
# so both are listed and the metric does not depend on visit_completed having a
# producer yet. 검수형 팬레터 / 디지털 체키 / 멤버십 are North Star actions too but
# are P1+ (no P0 event), so they are intentionally out of v0 (a documented gap).
_FOLLOWUP_EVENT_NAMES = (
    EventName.VISIT_CHECKED_IN.value,
    EventName.VISIT_COMPLETED.value,
    EventName.FAVORITE_ADDED.value,
    EventName.CHEKI_RECORDED.value,
    EventName.EVENT_RESERVED.value,
)
# Visit follow-up events get the invalidated-visit exclusion + the self-match
# guard (a visit must not satisfy its own MSFC).
_VISIT_FOLLOWUP_NAMES = frozenset(
    {EventName.VISIT_CHECKED_IN.value, EventName.VISIT_COMPLETED.value}
)


@dataclass(frozen=True)
class OperatorKpiMetrics:
    """The KPI set for one period, counts-only (no PII, names, or prices).

    Rates are fractions in ``[0.0, 1.0]`` and are ``0.0`` when their denominator
    is zero (a missing pool is not a divide-by-zero error). ``period_end`` is
    exclusive.
    """

    period_start: str
    period_end: str

    # --- North Star -------------------------------------------------------
    msfc: int
    verified_visit_fans: int
    safe_fan_continuation_rate: float

    # --- Retention / conversion ------------------------------------------
    first_visit_fans: int
    thirty_day_return_rate: float
    favorite_registrations: int
    favorite_to_visit_rate: float
    schedule_view_fans: int
    schedule_to_reservation_rate: float
    schedule_to_visit_rate: float

    # --- Platform activation ---------------------------------------------
    signups: int
    visitor_signup_rate: float
    favorite_registration_rate: float
    cheki_record_rate: float

    # --- Guardrails (North Star principle: never read MSFC alone) ---------
    safety_reports_created: int
    safety_report_rate_per_visit: float
    users_blocked: int
    excluded_risk_fans: int


@dataclass(frozen=True)
class _Visit:
    """A verified-offline check-in anchor (the fan and when/which visit)."""

    fan_id: str
    occurred_at: datetime
    visit_id: str


@dataclass(frozen=True)
class _FollowUp:
    """A candidate safe-continuation action (``visit_id`` empty if non-visit)."""

    occurred_at: datetime
    visit_id: str


def _rate(numerator: int, denominator: int) -> float:
    """Fraction with a zero-denominator guard (an empty pool reads as 0.0)."""
    return numerator / denominator if denominator else 0.0


def month_bounds(day: date_cls) -> tuple[datetime, datetime]:
    """Return the aware half-open ``[month_start, next_month_start)`` for [day]."""
    start_date = day.replace(day=1)
    if start_date.month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1)
    start = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end = timezone.make_aware(datetime.combine(end_date, datetime.min.time()))
    return start, end


def _invalidated_ids(event_name: str, key: str) -> set[str]:
    """The set of ids carried by corrective ``*_invalidated`` events.

    The append-only ledger never mutates the original ``visit_checked_in`` /
    ``cheki_recorded`` row, so a void is a separate event naming the id to
    exclude (mirrors ``count_msfc_starts``).
    """
    rows = EventRecord.objects.filter(event_name=event_name).values_list(
        f"payload__{key}", flat=True
    )
    return {str(value) for value in rows if value}


def _risk_excluded_fan_ids(*, as_of: datetime) -> set[str]:
    """Fans excluded as "위험 고객": an active block or an open report.

    Active is read from the safety models (status, lift-aware) rather than the
    ledger, because a lifted block emits no corrective event. Risk flags
    (soft) and open (non-closed) reports targeting a fan are included too, so a
    fan under review never counts toward a "safe" continuation.
    """
    blocked = UserBlock.objects.filter(
        status=BlockStatus.ACTIVE.value,
        effective_from__lte=as_of,
    ).values_list("target__fan_id", flat=True)
    open_reports = (
        SafetyReport.objects.filter(target_type=ActorKind.FAN.value)
        .exclude(status=ReportStatus.CLOSED.value)
        .exclude(target__isnull=True)
        .values_list("target__fan_id", flat=True)
    )
    return {str(fid) for fid in [*blocked, *open_reports] if fid}


def _valid_fan_events(event_names: list[str]) -> QuerySet[EventRecord]:
    """Valid, fan-attributed, non-operator events of one or more types.

    The shared filter for every metric: a completed (not refunded/cancelled via
    its own status) action by a known fan that is neither operator traffic nor a
    quality-flagged test/dummy row (North Star excludes 운영자/직원 테스트/더미).
    Action-level corrections that arrive as *separate* append-only events
    (``*_invalidated``, ``reservation_cancelled``) are netted by the callers that
    can link them by id.
    """
    return (
        EventRecord.objects.filter(
            event_name__in=event_names,
            status=EventStatus.COMPLETED.value,
            is_invalidated=False,
            actor_is_operator=False,
        )
        .exclude(fan_id="")
        # NULL-safe test/dummy exclusion: drop a row only when quality.is_test is
        # explicitly True; an absent key (the default {}) reads as real traffic, so
        # a plain .exclude(quality__is_test=True) (which also drops NULLs) is wrong.
        .filter(Q(quality__is_test__isnull=True) | Q(quality__is_test=False))
    )


def _completed_fan_events(event_name: str) -> QuerySet[EventRecord]:
    """Valid, fan-attributed, non-operator events of a single type."""
    return _valid_fan_events([event_name])


def _cancelled_reservation_ids() -> set[str]:
    """``reservation_id``s cancelled by a later ``reservation_cancelled`` event.

    Reservations/event reservations are append-only, so a cancellation is a new
    event; an ``event_reserved`` / ``reservation_created`` whose id appears here
    is netted out (North Star excludes 취소된 행동). ``payment_refunded`` carries
    no target id in the P0 schema, so refund-by-payment cannot yet be attributed
    to a specific action — a documented v1 gap (Data_Event_Schema).
    """
    rows = EventRecord.objects.filter(event_name=EventName.RESERVATION_CANCELLED.value).values_list(
        "payload__reservation_id", flat=True
    )
    return {str(value) for value in rows if value}


def _verified_visits(start: datetime, end: datetime) -> QuerySet[EventRecord]:
    """Verified-offline check-ins in ``[start, end)`` eligible to start an MSFC."""
    invalid_visits = _invalidated_ids(EventName.VISIT_INVALIDATED.value, "visit_id")
    return (
        _completed_fan_events(EventName.VISIT_CHECKED_IN.value)
        .filter(
            payload__is_verified_offline_visit=True,
            occurred_at__gte=start,
            occurred_at__lt=end,
        )
        .exclude(visit_id__in=invalid_visits)
    )


def _unique_fans(queryset: QuerySet[EventRecord]) -> set[str]:
    """The distinct non-empty ``fan_id`` set of a queryset."""
    return {str(fid) for fid in queryset.values_list("fan_id", flat=True) if fid}


def _followups_by_fan(fan_ids: set[str], horizon_end: datetime) -> dict[str, list[_FollowUp]]:
    """Map each fan to their valid safe-continuation actions up to [horizon_end].

    One query over the candidate fans (bounded by the 30-day horizon past the
    window) instead of a per-anchor lookup. Cheki actions whose ``cheki_id`` was
    later voided are dropped via the corrective-event id set.
    """
    if not fan_ids:
        return {}
    invalid_chekis = _invalidated_ids(EventName.CHEKI_INVALIDATED.value, "cheki_id")
    invalid_visits = _invalidated_ids(EventName.VISIT_INVALIDATED.value, "visit_id")
    cancelled_reservations = _cancelled_reservation_ids()
    rows = (
        _valid_fan_events(list(_FOLLOWUP_EVENT_NAMES))
        .filter(
            fan_id__in=fan_ids,
            occurred_at__lt=horizon_end,
        )
        .values_list("fan_id", "event_name", "occurred_at", "visit_id", "payload")
    )
    by_fan: dict[str, list[_FollowUp]] = defaultdict(list)
    for fan_id, event_name, occurred_at, visit_id, payload in rows:
        data = payload or {}
        if event_name == EventName.CHEKI_RECORDED.value:
            if str(data.get("cheki_id", "")) in invalid_chekis:
                continue
        elif event_name in _VISIT_FOLLOWUP_NAMES:
            if str(visit_id) in invalid_visits:
                continue
        elif event_name == EventName.EVENT_RESERVED.value:
            if str(data.get("reservation_id", "")) in cancelled_reservations:
                continue
        is_visit = event_name in _VISIT_FOLLOWUP_NAMES
        by_fan[str(fan_id)].append(
            _FollowUp(occurred_at=occurred_at, visit_id=str(visit_id) if is_visit else "")
        )
    return by_fan


def _has_safe_followup(anchors: list[_Visit], followups: list[_FollowUp]) -> bool:
    """Whether any anchor visit is followed by a distinct safe action ≤30 days.

    A follow-up qualifies when it occurs strictly after an anchor, within
    [MSFC_WINDOW], and — for a revisit (another check-in) — is a *different*
    visit than the anchor (so a visit never satisfies itself).
    """
    for anchor in anchors:
        deadline = anchor.occurred_at + MSFC_WINDOW
        for followup in followups:
            if followup.occurred_at <= anchor.occurred_at:
                continue
            if followup.occurred_at > deadline:
                continue
            if followup.visit_id and followup.visit_id == anchor.visit_id:
                continue
            return True
    return False


def _converted_fans(
    anchor_fans: set[str],
    target_queryset: QuerySet[EventRecord],
    anchor_times: dict[str, list[datetime]],
    window: timedelta,
) -> int:
    """Count anchor fans with a target action within [window] after an anchor."""
    if not anchor_fans:
        return 0
    target_times: dict[str, list[datetime]] = defaultdict(list)
    for fan_id, occurred_at in target_queryset.filter(fan_id__in=anchor_fans).values_list(
        "fan_id", "occurred_at"
    ):
        target_times[str(fan_id)].append(occurred_at)
    converted = 0
    for fan_id in anchor_fans:
        if any(
            anchor < target <= anchor + window
            for anchor in anchor_times.get(fan_id, [])
            for target in target_times.get(fan_id, [])
        ):
            converted += 1
    return converted


def operator_kpi_metrics(*, period_start: datetime, period_end: datetime) -> OperatorKpiMetrics:
    """Project the operator KPI set for the half-open window ``[start, end)``.

    Reads the append-only ledger plus the safety models (for the risk-fan
    exclusion). Counts and rates only — never names, narrative, or prices.

    Risk-fan exclusion scope: "위험 고객" (active block / open report) are removed
    from MSFC and its denominator ``verified_visit_fans`` only — the North Star
    exclusion clause is written against MSFC. The other rate pools (return,
    favorite, schedule, signup/activation) use the canonical per-action
    denominators and are intentionally not risk-filtered, so e.g. a blocked fan
    still appears in ``first_visit_fans``/``signups``.

    Scope: ``msfc`` is the monthly North Star (a *visit-cohort*: a fan whose
    verified visit is in the window with a safe follow-up within 30 days of that
    visit). The Weekly_KPI "주간 MSFC 후보" hybrid (visit-in-week OR
    follow-up-completed-in-week) is a separate weekly leading indicator, out of
    this v0 scope.
    """
    excluded = _risk_excluded_fan_ids(as_of=period_end)
    horizon_end = period_end + MSFC_WINDOW
    # Correction sets, applied to every visit/reservation scan below so a voided
    # visit or a cancelled reservation never counts as a safe action / conversion.
    invalid_visits = _invalidated_ids(EventName.VISIT_INVALIDATED.value, "visit_id")
    cancelled_reservations = _cancelled_reservation_ids()

    # --- MSFC + Safe Fan Continuation Rate -------------------------------
    verified = list(
        _verified_visits(period_start, period_end).values_list("fan_id", "occurred_at", "visit_id")
    )
    anchors_by_fan: dict[str, list[_Visit]] = defaultdict(list)
    for fan_id, occurred_at, visit_id in verified:
        fid = str(fan_id)
        if fid in excluded:
            continue
        anchors_by_fan[fid].append(
            _Visit(fan_id=fid, occurred_at=occurred_at, visit_id=str(visit_id))
        )
    verified_visit_fans = len(anchors_by_fan)
    followups = _followups_by_fan(set(anchors_by_fan), horizon_end)
    msfc = sum(
        1
        for fid, anchors in anchors_by_fan.items()
        if _has_safe_followup(anchors, followups.get(fid, []))
    )

    # --- 30-Day Return Rate (first-visit cohort in the window) -----------
    first_visit_fans, returned = _return_rate_inputs(period_start, period_end)

    # --- Favorite-to-Visit Conversion (30 days) --------------------------
    favorites_qs = _completed_fan_events(EventName.FAVORITE_ADDED.value).filter(
        occurred_at__gte=period_start, occurred_at__lt=period_end
    )
    favorite_fans = _unique_fans(favorites_qs)
    favorite_times: dict[str, list[datetime]] = defaultdict(list)
    for fan_id, occurred_at in favorites_qs.values_list("fan_id", "occurred_at"):
        favorite_times[str(fan_id)].append(occurred_at)
    favorite_to_visit = _converted_fans(
        favorite_fans,
        _completed_fan_events(EventName.VISIT_CHECKED_IN.value)
        .filter(occurred_at__lt=horizon_end)
        .exclude(visit_id__in=invalid_visits),
        favorite_times,
        MSFC_WINDOW,
    )

    # --- Schedule-view → reservation / visit conversion (7 days) ---------
    schedule_qs = _completed_fan_events(EventName.SCHEDULE_VIEWED.value).filter(
        occurred_at__gte=period_start, occurred_at__lt=period_end
    )
    schedule_fans = _unique_fans(schedule_qs)
    schedule_times: dict[str, list[datetime]] = defaultdict(list)
    for fan_id, occurred_at in schedule_qs.values_list("fan_id", "occurred_at"):
        schedule_times[str(fan_id)].append(occurred_at)
    convert_end = period_end + SCHEDULE_CONVERSION_WINDOW
    schedule_to_reservation = _converted_fans(
        schedule_fans,
        _completed_fan_events(EventName.RESERVATION_CREATED.value)
        .filter(occurred_at__lt=convert_end)
        .exclude(payload__reservation_id__in=cancelled_reservations),
        schedule_times,
        SCHEDULE_CONVERSION_WINDOW,
    )
    schedule_to_visit = _converted_fans(
        schedule_fans,
        _completed_fan_events(EventName.VISIT_CHECKED_IN.value)
        .filter(occurred_at__lt=convert_end)
        .exclude(visit_id__in=invalid_visits),
        schedule_times,
        SCHEDULE_CONVERSION_WINDOW,
    )

    # --- Platform activation rates ---------------------------------------
    # visitor_signup_rate puts (non-risk-filtered) signups over the risk-filtered
    # verified_visit_fans, so the pools differ by the risk exclusion; it is a
    # directional activation rate (the canonical 방문자 회원가입률), not a closed
    # cohort ratio, so it can exceed 1.0.
    signup_fans = _unique_fans(
        _completed_fan_events(EventName.FAN_SIGNED_UP.value).filter(
            occurred_at__gte=period_start, occurred_at__lt=period_end
        )
    )
    cheki_fans = _unique_fans(
        _completed_fan_events(EventName.CHEKI_RECORDED.value).filter(
            occurred_at__gte=period_start, occurred_at__lt=period_end
        )
    )

    # --- Guardrails -------------------------------------------------------
    # The per-visit denominator is fan (non-operator) check-ins, consistent with
    # every other visit-derived figure: operator/test traffic must never dilute a
    # safety rate (North Star operator-exclusion is global). The numerator counts
    # all reports filed (operators file them — that is correct).
    visit_fan_count = (
        _completed_fan_events(EventName.VISIT_CHECKED_IN.value)
        .filter(occurred_at__gte=period_start, occurred_at__lt=period_end)
        .exclude(visit_id__in=invalid_visits)
        .count()
    )
    reports_created = _day_window_count(
        EventName.SAFETY_REPORT_CREATED.value, period_start, period_end
    )
    users_blocked = _day_window_count(EventName.USER_BLOCKED.value, period_start, period_end)

    return OperatorKpiMetrics(
        period_start=period_start.date().isoformat(),
        period_end=period_end.date().isoformat(),
        msfc=msfc,
        verified_visit_fans=verified_visit_fans,
        safe_fan_continuation_rate=_rate(msfc, verified_visit_fans),
        first_visit_fans=first_visit_fans,
        thirty_day_return_rate=_rate(returned, first_visit_fans),
        favorite_registrations=len(favorite_fans),
        favorite_to_visit_rate=_rate(favorite_to_visit, len(favorite_fans)),
        schedule_view_fans=len(schedule_fans),
        schedule_to_reservation_rate=_rate(schedule_to_reservation, len(schedule_fans)),
        schedule_to_visit_rate=_rate(schedule_to_visit, len(schedule_fans)),
        signups=len(signup_fans),
        visitor_signup_rate=_rate(len(signup_fans), verified_visit_fans),
        favorite_registration_rate=_rate(len(favorite_fans & signup_fans), len(signup_fans)),
        cheki_record_rate=_rate(len(cheki_fans & signup_fans), len(signup_fans)),
        safety_reports_created=reports_created,
        safety_report_rate_per_visit=_rate(reports_created, visit_fan_count),
        users_blocked=users_blocked,
        excluded_risk_fans=len(excluded),
    )


def _day_window_count(event_name: str, start: datetime, end: datetime) -> int:
    """Gross count of an event in ``[start, end)`` (excludes invalidated rows)."""
    return EventRecord.objects.filter(
        event_name=event_name,
        occurred_at__gte=start,
        occurred_at__lt=end,
        is_invalidated=False,
    ).count()


def _return_rate_inputs(start: datetime, end: datetime) -> tuple[int, int]:
    """First-visit fans in the window and how many returned within 30 days.

    A "first visit" is a fan whose earliest-ever ``visit_checked_in`` falls in
    ``[start, end)``; they "returned" if a *distinct* later visit — a check-in or
    a completion (North Star "체크인 또는 결제") — occurs within 30 days.
    Earliest-ever (not earliest-in-window) avoids miscounting an established fan
    as new. Invalidated visits are excluded from both legs, and the scan is
    bounded above by ``end + 30d`` (any relevant visit occurs before then).
    """
    horizon = end + MSFC_WINDOW
    invalid_visits = _invalidated_ids(EventName.VISIT_INVALIDATED.value, "visit_id")
    checkins = (
        _completed_fan_events(EventName.VISIT_CHECKED_IN.value)
        .filter(occurred_at__lt=horizon)
        .exclude(visit_id__in=invalid_visits)
    )
    earliest: dict[str, tuple[datetime, str]] = {}
    for fan_id, occurred_at, visit_id in checkins.values_list("fan_id", "occurred_at", "visit_id"):
        fid = str(fan_id)
        if fid not in earliest or occurred_at < earliest[fid][0]:
            earliest[fid] = (occurred_at, str(visit_id))

    # The return leg may be a re-entry (check-in) or a completed visit.
    visits_by_fan: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    return_legs = (
        _valid_fan_events(list(_VISIT_FOLLOWUP_NAMES))
        .filter(occurred_at__lt=horizon)
        .exclude(visit_id__in=invalid_visits)
    )
    for fan_id, occurred_at, visit_id in return_legs.values_list(
        "fan_id", "occurred_at", "visit_id"
    ):
        visits_by_fan[str(fan_id)].append((occurred_at, str(visit_id)))

    first_visit_fans = 0
    returned = 0
    for fid, (first_at, first_visit_id) in earliest.items():
        if not (start <= first_at < end):
            continue
        first_visit_fans += 1
        deadline = first_at + MSFC_WINDOW
        if any(
            first_at < other <= deadline and vid != first_visit_id
            for other, vid in visits_by_fan[fid]
        ):
            returned += 1
    return first_visit_fans, returned
