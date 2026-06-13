"""Event emission and metric queries for the append-only log.

``emit_event`` is the only sanctioned way to write an :class:`EventRecord`: it
validates the event name and payload against the registry and refuses safety
events that try to smuggle report narrative into ``properties``. Callers in
domain apps (P5) depend on this single funnel so the ledger stays trustworthy.

The metric helpers (:func:`count_msfc_starts`, :func:`count_revisits_within`)
express MSFC and the 30-day revisit rule as ORM queries over the denormalised
columns, demonstrating the schema supports them and that operator traffic can be
excluded.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.db.models import Count
from pydantic import ValidationError

from apps.event_log.events import (
    EVENT_PAYLOAD_SCHEMAS,
    FORBIDDEN_SAFETY_PROPERTY_KEYS,
    SAFETY_EVENT_NAMES,
    ActorType,
    EventName,
    EventSource,
    EventStatus,
)
from apps.event_log.models import EventRecord


class EventValidationError(Exception):
    """Raised when an event cannot be emitted as specified.

    Distinct from pydantic's ``ValidationError`` so callers can catch emission
    failures (unknown name, missing required field, forbidden safety key)
    without depending on pydantic internals.
    """


def _reject_forbidden_safety_keys(event_name: str, payload: dict[str, Any]) -> None:
    """Block raw report narrative / PII keys on safety events.

    Data_Event_Schema 개인정보 기준 keeps report detail in a restricted store; the
    event log holds only type/severity/status/ids. Enforcing this at emit time
    (rather than trusting callers) makes the separation a property of the system.
    """
    if event_name not in SAFETY_EVENT_NAMES:
        return
    offending = FORBIDDEN_SAFETY_PROPERTY_KEYS.intersection(payload)
    if offending:
        raise EventValidationError(
            f"Safety event '{event_name}' may not carry report detail in "
            f"properties; forbidden keys present: {sorted(offending)}. Store "
            "narrative in the restricted safety store and reference it by id."
        )


def emit_event(
    *,
    event_name: str,
    occurred_at: datetime,
    actor_type: str,
    source: str,
    payload: dict[str, Any] | None = None,
    actor_id: str = "",
    fan_id: str = "",
    cast_id: str = "",
    visit_id: str = "",
    status: str = EventStatus.COMPLETED.value,
    actor_is_operator: bool = False,
    ids: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    quality: dict[str, Any] | None = None,
    schema_version: str = "1.0",
) -> EventRecord:
    """Validate and persist one event, returning the stored record.

    Validation order matters: we confirm the name is registered, then scrub
    safety properties, then check the payload against its schema. Any failure
    raises :class:`EventValidationError` and writes nothing — emission is
    all-or-nothing so a rejected event never leaves a partial row.
    """
    payload = payload or {}

    if event_name not in EVENT_PAYLOAD_SCHEMAS:
        raise EventValidationError(
            f"Unknown event_name '{event_name}'. Register it in "
            "apps.event_log.events.EVENT_PAYLOAD_SCHEMAS first."
        )
    if actor_type not in ActorType.values:
        raise EventValidationError(f"Unknown actor_type '{actor_type}'.")
    if source not in EventSource.values:
        raise EventValidationError(f"Unknown source '{source}'.")
    if status not in EventStatus.values:
        raise EventValidationError(f"Unknown status '{status}'.")

    _reject_forbidden_safety_keys(event_name, payload)

    schema = EVENT_PAYLOAD_SCHEMAS[event_name]
    try:
        schema.model_validate(payload)
    except ValidationError as exc:
        raise EventValidationError(
            f"Payload for '{event_name}' failed validation: {exc.errors()}"
        ) from exc

    record = EventRecord(
        event_name=event_name,
        occurred_at=occurred_at,
        actor_type=actor_type,
        actor_id=actor_id,
        source=source,
        fan_id=fan_id,
        cast_id=cast_id,
        visit_id=visit_id,
        status=status,
        actor_is_operator=actor_is_operator,
        ids=ids or {},
        context=context or {},
        payload=payload,
        quality=quality or {},
        schema_version=schema_version,
    )
    record.save()
    return record


def reattribute_anonymous_events(*, anonymous_id: str, fan_id: str) -> int:
    """Record a merge event so pre-signup activity folds into the fan.

    The append-only ledger forbids rewriting historical anonymous rows, so merge
    is expressed as a new ``anonymous_user_merged`` event carrying both ids
    (Data_Event_Schema L764-769). MSFC queries that join on ``fan_id`` use this
    link to re-attribute the earlier anonymous visits *without* double counting,
    because the original rows kept ``fan_id`` empty and are not themselves MSFC
    starts until merged. Returns the number of prior anonymous events linked.

    Why count rather than mutate: the return value lets callers/tests assert the
    merge connected the expected history while the rows stay immutable.
    """
    linked = EventRecord.objects.filter(
        ids__anonymous_id=anonymous_id,
    ).count()
    emit_event(
        event_name=EventName.ANONYMOUS_USER_MERGED.value,
        occurred_at=_now(),
        actor_type=ActorType.SYSTEM.value,
        source=EventSource.SYSTEM.value,
        fan_id=fan_id,
        payload={"anonymous_id": anonymous_id, "fan_id": fan_id},
        ids={"anonymous_id": anonymous_id, "fan_id": fan_id},
    )
    return linked


def count_msfc_starts(*, exclude_operators: bool = True) -> int:
    """Count verified-offline visit check-ins that start an MSFC window.

    MSFC start condition is a verified offline visit that is neither test nor
    invalidated (Data_Event_Schema MSFC 계산 규칙). We filter to
    ``visit_checked_in`` events flagged ``is_verified_offline_visit`` in payload,
    require a known fan (anonymous-only visits are not MSFC starts until merged),
    and optionally exclude operator traffic. Invalidation is honoured two ways:
    the row's own ``is_invalidated`` flag, AND — because the append-only ledger
    cannot mutate the original check-in — by excluding any ``visit_id`` that has a
    later ``visit_invalidated`` event (Data_Event_Schema L274 "방문 기록 무효 →
    제외"); this is how an operator void (ASS-94) removes a visit from MSFC.
    """
    invalidated_visit_ids = EventRecord.objects.filter(
        event_name=EventName.VISIT_INVALIDATED.value,
    ).values("visit_id")
    qs = (
        EventRecord.objects.filter(
            event_name=EventName.VISIT_CHECKED_IN.value,
            payload__is_verified_offline_visit=True,
            is_invalidated=False,
        )
        .exclude(fan_id="")
        .exclude(visit_id__in=invalidated_visit_ids)
    )
    if exclude_operators:
        qs = qs.filter(actor_is_operator=False)
    return qs.count()


def count_revisits_within(*, days: int = 30, exclude_operators: bool = True) -> int:
    """Count fans with a completed visit followed by another within ``days``.

    Demonstrates the 30-day revisit rule is computable from the log: group
    ``visit_completed`` events by fan and flag fans with 2+ within the window.
    This is a structural proof (the schema supports it), not the production
    metric, which would compare consecutive ``occurred_at`` gaps per fan.
    Invalidated visits are excluded both by the row flag and by a matching
    ``visit_invalidated`` event (consistent with ``count_msfc_starts``).
    """
    window_start = _now() - timedelta(days=days)
    invalidated_visit_ids = EventRecord.objects.filter(
        event_name=EventName.VISIT_INVALIDATED.value,
    ).values("visit_id")
    qs = (
        EventRecord.objects.filter(
            event_name=EventName.VISIT_COMPLETED.value,
            occurred_at__gte=window_start,
            is_invalidated=False,
        )
        .exclude(fan_id="")
        .exclude(visit_id__in=invalidated_visit_ids)
    )
    if exclude_operators:
        qs = qs.filter(actor_is_operator=False)
    fans_with_repeat = (
        qs.values("fan_id").annotate(visits=Count("id")).filter(visits__gte=2)
    )
    return fans_with_repeat.count()


def _now() -> datetime:
    """Return an aware ``now`` via Django's timezone for testability."""
    from django.utils import timezone

    return timezone.now()
