"""Service layer for operator cast-schedule management (ASS-93).

Every mutation is audited. Changes to a *published* entry go through an
approval: :func:`request_change` files a :class:`ScheduleChangeRequest`, and
:func:`approve_change` (by a *different* staff member — separation of duties)
applies it. Draft entries are editable directly since they are not yet visible.
Entries are never deleted; ``unpublish_entry`` hides them (비공개).

No analytics event is emitted here — schedule management is operational; the
fan-facing ``schedule_viewed`` KPI event lives on the fan read path.
"""

from __future__ import annotations

from datetime import date as date_cls
from datetime import time
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.identity.models import Account
from apps.schedule.models import (
    ChangeRequestStatus,
    ScheduleChangeRequest,
    ScheduleEntry,
    ScheduleStatus,
)

# Fields a change request may override on an entry.
_CHANGEABLE_FIELDS = ("work_date", "start_time", "end_time", "note")


@transaction.atomic
def create_entry(
    *,
    work_date: date_cls,
    cast_id: str,
    start_time: time,
    end_time: time,
    actor: Account,
    note: str = "",
) -> ScheduleEntry:
    """Create a draft schedule entry (not visible to fans until published)."""
    entry = ScheduleEntry.objects.create(
        work_date=work_date,
        cast_id=cast_id,
        start_time=start_time,
        end_time=end_time,
        note=note,
        created_by=actor,
    )
    record_audit(
        actor=actor,
        action=AuditAction.SCHEDULE_CREATED.value,
        target=str(entry.id),
        metadata={"cast_id": cast_id, "work_date": work_date.isoformat()},
    )
    return entry


@transaction.atomic
def edit_draft(
    entry: ScheduleEntry,
    *,
    actor: Account,
    work_date: date_cls | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
    note: str | None = None,
) -> ScheduleEntry:
    """Edit a DRAFT entry directly. Published entries must use request_change."""
    if entry.status != ScheduleStatus.DRAFT.value:
        raise ValueError("Only draft entries can be edited directly; request a change.")
    before = _snapshot(entry)
    if work_date is not None:
        entry.work_date = work_date
    if start_time is not None:
        entry.start_time = start_time
    if end_time is not None:
        entry.end_time = end_time
    if note is not None:
        entry.note = note
    entry.save(
        update_fields=["work_date", "start_time", "end_time", "note", "updated_at"]
    )
    record_audit(
        actor=actor,
        action=AuditAction.SCHEDULE_EDITED.value,
        target=str(entry.id),
        metadata={"before": before, "after": _snapshot(entry)},
    )
    return entry


@transaction.atomic
def publish_entry(entry: ScheduleEntry, *, actor: Account) -> ScheduleEntry:
    """Publish a draft/unpublished entry so fans can see it."""
    entry.status = ScheduleStatus.PUBLISHED.value
    entry.save(update_fields=["status", "updated_at"])
    record_audit(
        actor=actor,
        action=AuditAction.SCHEDULE_PUBLISHED.value,
        target=str(entry.id),
    )
    return entry


@transaction.atomic
def unpublish_entry(
    entry: ScheduleEntry, *, actor: Account, reason: str = ""
) -> ScheduleEntry:
    """Hide an entry from fans (비공개) without deleting it."""
    entry.status = ScheduleStatus.UNPUBLISHED.value
    entry.save(update_fields=["status", "updated_at"])
    record_audit(
        actor=actor,
        action=AuditAction.SCHEDULE_UNPUBLISHED.value,
        target=str(entry.id),
        reason=reason,
    )
    return entry


@transaction.atomic
def request_change(
    *,
    entry: ScheduleEntry,
    proposed: dict[str, str],
    reason: str,
    actor: Account,
) -> ScheduleChangeRequest:
    """File a pending change to a published entry (applied only on approval)."""
    if entry.status != ScheduleStatus.PUBLISHED.value:
        raise ValueError("Change requests apply to published entries only.")
    # Validate keys AND value parseability now, so the *requester* gets the error
    # instead of it surfacing cryptically at approve time (and never resolving).
    _parse_proposed(proposed)
    request = ScheduleChangeRequest.objects.create(
        entry=entry,
        proposed=proposed,
        before=_snapshot(entry),
        reason=reason,
        requested_by=actor,
    )
    record_audit(
        actor=actor,
        action=AuditAction.SCHEDULE_CHANGE_REQUESTED.value,
        target=str(entry.id),
        reason=reason,
        metadata={"change_request_id": str(request.id), "proposed": proposed},
    )
    return request


@transaction.atomic
def approve_change(
    *, request: ScheduleChangeRequest, actor: Account, decision_note: str = ""
) -> ScheduleChangeRequest:
    """Apply a pending change to its entry (approver must differ from requester)."""
    if request.status != ChangeRequestStatus.PENDING.value:
        raise ValueError("Only a pending change request can be approved.")
    if request.requested_by_id == actor.pk:
        # Separation of duties: 변경은 다른 운영 직원의 승인으로 반영된다.
        raise ValueError("A change must be approved by a different staff member.")
    entry = request.entry
    for field, value in _parse_proposed(request.proposed).items():
        setattr(entry, field, value)
    entry.save(
        update_fields=["work_date", "start_time", "end_time", "note", "updated_at"]
    )
    request.status = ChangeRequestStatus.APPROVED.value
    request.decided_by = actor
    request.decided_at = timezone.now()
    request.decision_note = decision_note
    request.save(
        update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"]
    )
    record_audit(
        actor=actor,
        action=AuditAction.SCHEDULE_CHANGE_APPROVED.value,
        target=str(entry.id),
        metadata={
            "change_request_id": str(request.id),
            "before": request.before,
            "after": _snapshot(entry),
        },
    )
    return request


@transaction.atomic
def reject_change(
    *, request: ScheduleChangeRequest, actor: Account, decision_note: str = ""
) -> ScheduleChangeRequest:
    """Reject a pending change request without touching the entry."""
    if request.status != ChangeRequestStatus.PENDING.value:
        raise ValueError("Only a pending change request can be rejected.")
    request.status = ChangeRequestStatus.REJECTED.value
    request.decided_by = actor
    request.decided_at = timezone.now()
    request.decision_note = decision_note
    request.save(
        update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"]
    )
    record_audit(
        actor=actor,
        action=AuditAction.SCHEDULE_CHANGE_REJECTED.value,
        target=str(request.entry_id),
        metadata={"change_request_id": str(request.id)},
    )
    return request


def _snapshot(entry: ScheduleEntry) -> dict[str, str]:
    """Comparable string snapshot of an entry's mutable fields."""
    return {
        "work_date": entry.work_date.isoformat(),
        "start_time": entry.start_time.isoformat(),
        "end_time": entry.end_time.isoformat(),
        "note": entry.note,
    }


def _parse_proposed(proposed: dict[str, Any]) -> dict[str, Any]:
    """Validate proposed keys and parse values into typed entry fields.

    Single source of truth used by both ``request_change`` (fail-fast at request
    time) and ``approve_change`` (apply). Unknown keys, non-string values, and
    unparseable date/time strings all raise ``ValueError`` — which the API maps
    to 400 — so a bad change never sits PENDING forever and a non-HTTP caller
    cannot trigger a 500 via a stray ``TypeError``.
    """
    unknown = set(proposed) - set(_CHANGEABLE_FIELDS)
    if unknown:
        raise ValueError(f"Unchangeable fields: {sorted(unknown)}.")
    parsed: dict[str, Any] = {}
    for field, value in proposed.items():
        if not isinstance(value, str):
            raise ValueError(f"Field '{field}' must be a string.")
        if field == "work_date":
            parsed[field] = date_cls.fromisoformat(value)
        elif field in ("start_time", "end_time"):
            parsed[field] = time.fromisoformat(value)
        else:  # note
            parsed[field] = value
    return parsed
