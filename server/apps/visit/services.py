"""Service layer for operator-managed visit records.

Every visit mutation passes through this module so the operational row, the audit
trail, and the append-only analytics event stay coupled. Analytics events are
emitted **only** through :func:`apps.event_log.services.emit_event`, which
validates the name and payload against the canonical registry — domain apps never
write :class:`~apps.event_log.models.EventRecord` directly, or the ledger's
integrity guarantees (MSFC, 30-day revisit) erode.

Event mapping (Data_Event_Schema):

- manual check-in     → ``visit_checked_in``  (the canonical MSFC start event)
- void / invalidate   → ``visit_invalidated`` (the canonical exclusion event)
- metadata correction → **audit only**; editing a note or timestamp is an
  operational fix, not an analytics fact, so it has no canonical event.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import emit_event
from apps.identity.models import Account
from apps.visit.models import VisitRecord, VisitRecordSource, VisitRecordStatus

# A manual check-in whose visited_at is older than this is treated as a backfill
# (Data_Event_Schema quality.is_backfilled): recorded materially after the fact,
# so reports can annotate the correction. Small tolerance absorbs the normal gap
# between a visit and the operator entering it in the same session.
_BACKFILL_TOLERANCE = timedelta(minutes=5)


@transaction.atomic
def record_visit(
    *,
    fan: Account,
    visited_at: datetime,
    note: str = "",
    actor: Account,
) -> VisitRecord:
    """Create a manual visit and record its audit + analytics side effects.

    Manual check-in is an operator action that nonetheless represents a *real*
    fan visit, so it emits the canonical ``visit_checked_in`` event with
    ``actor_is_operator=False``: it must count toward MSFC exactly like a QR
    check-in (it is the QR-fallback path, ASS-99). The operator's identity is
    preserved in ``checkin_method=operator`` and ``created_by_operator_id`` for
    provenance, not as a metric-exclusion flag.
    """
    visited_at = _ensure_aware(visited_at)
    record = VisitRecord.objects.create(
        fan=fan,
        visited_at=visited_at,
        note=note,
        created_by=actor,
        source=VisitRecordSource.OPERATOR_MANUAL.value,
    )
    record_audit(
        actor=actor,
        action=AuditAction.VISIT_RECORDED.value,
        target=str(record.id),
        metadata={
            "fan_id": str(fan.fan_id),
            "visited_at": visited_at.isoformat(),
            "note_present": bool(note.strip()),
        },
    )
    business_day = _business_day(visited_at)
    emit_event(
        event_name=EventName.VISIT_CHECKED_IN.value,
        occurred_at=visited_at,
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_id=str(actor.fan_id),
        fan_id=str(fan.fan_id),
        visit_id=str(record.id),
        # A genuine fan visit recorded by an operator is NOT excluded traffic.
        actor_is_operator=False,
        ids={"fan_id": str(fan.fan_id), "visit_id": str(record.id)},
        context={"store_id": record.store_id, "business_day": business_day},
        payload={
            "visit_id": str(record.id),
            "store_id": record.store_id,
            "business_day": business_day,
            "visit_type": "manual",
            "checkin_method": "operator",
            "is_verified_offline_visit": True,
        },
        # quality (Data_Event_Schema L217/L857): operator provenance and the
        # backfill flag belong here, not in properties.
        quality={
            "created_by_operator_id": str(actor.fan_id),
            "is_backfilled": visited_at < timezone.now() - _BACKFILL_TOLERANCE,
        },
    )
    return record


@transaction.atomic
def correct_visit(
    record: VisitRecord,
    *,
    visited_at: datetime | None = None,
    note: str | None = None,
    actor: Account,
) -> VisitRecord:
    """Correct mutable visit fields, recording before/after audit evidence.

    No analytics event is emitted: a note/timestamp fix is an operational
    correction, and the canonical schema has no ``visit_corrected`` event. The
    accountability trail lives in the audit log; a correction that ever needs to
    change an *analytics* fact must be expressed as a new canonical event.
    """
    if visited_at is None and note is None:
        # No-op correction: don't manufacture an audit entry with identical
        # before/after.
        return record
    before = _snapshot(record)
    update_fields = ["updated_at"]
    if visited_at is not None:
        record.visited_at = _ensure_aware(visited_at)
        update_fields.append("visited_at")
    if note is not None:
        record.note = note
        update_fields.append("note")

    record.save(update_fields=update_fields)
    record.refresh_from_db()
    after = _snapshot(record)
    record_audit(
        actor=actor,
        action=AuditAction.VISIT_CORRECTED.value,
        target=str(record.id),
        metadata={"before": before, "after": after},
    )
    return record


@transaction.atomic
def void_visit(*, record: VisitRecord, reason: str, actor: Account) -> VisitRecord:
    """Void a visit record instead of deleting it, emitting the exclusion event.

    The operational row flips to ``voided`` (never deleted, for POS/audit trail)
    and the canonical ``visit_invalidated`` event is appended so analytics can
    exclude the visit. The original ``visit_checked_in`` row is left untouched
    (append-only); excluding it from MSFC is the metric query's job via the
    matching ``visit_invalidated`` event.

    Re-voiding is rejected: a second void with a different reason would obscure
    the first accountability decision rather than add useful state.
    """
    if record.status == VisitRecordStatus.VOIDED.value:
        raise ValueError("Visit record is already voided.")
    if not reason.strip():
        raise ValueError("Void reason is required.")

    before = _snapshot(record)
    record.status = VisitRecordStatus.VOIDED.value
    record.void_reason = reason.strip()
    record.save(update_fields=["status", "void_reason", "updated_at"])
    record.refresh_from_db()
    after = _snapshot(record)
    record_audit(
        actor=actor,
        action=AuditAction.VISIT_VOIDED.value,
        target=str(record.id),
        reason=record.void_reason,
        metadata={"before": before, "after": after},
    )
    emit_event(
        event_name=EventName.VISIT_INVALIDATED.value,
        # The invalidation happens now, not at the original visit time.
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_id=str(actor.fan_id),
        fan_id=str(record.fan.fan_id),
        visit_id=str(record.id),
        actor_is_operator=False,
        ids={"fan_id": str(record.fan.fan_id), "visit_id": str(record.id)},
        # Bucket the invalidation into the original visit's store/business_day so
        # daily/store reports net it against the check-in it cancels.
        context={
            "store_id": record.store_id,
            "business_day": _business_day(record.visited_at),
        },
        payload={"visit_id": str(record.id), "reason": record.void_reason},
    )
    return record


def _snapshot(record: VisitRecord) -> dict[str, str]:
    """Return the fields reviewers need to compare a visit mutation."""
    return {
        "visited_at": record.visited_at.isoformat(),
        "note": record.note,
        "status": record.status,
        "void_reason": record.void_reason,
    }


def _ensure_aware(value: datetime) -> datetime:
    """Coerce a naive datetime to the project timezone.

    Callers may pass a naive ISO datetime from the API; storing and emitting an
    aware value keeps ``business_day`` and ledger timestamps unambiguous.
    """
    if timezone.is_naive(value):
        return timezone.make_aware(value)
    return value


def _business_day(visited_at: datetime) -> str:
    """Derive the business day (local calendar date) for the visit event.

    Release 0.1 uses the local calendar date; a late-night cutoff (visits after
    midnight counting to the prior business day) is a future refinement for when
    store hours are configured.
    """
    return timezone.localdate(visited_at).isoformat()
