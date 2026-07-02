"""Operator API for cast-schedule management (ASS-93).

All routes are operator+. A change to a published entry is filed via
`POST /entries/{id}/changes` and applied only when a *different* operator calls
`POST /changes/{id}/approve` (separation of duties enforced in the service).
"""

from __future__ import annotations

import uuid
from datetime import date as date_cls
from datetime import datetime, time
from typing import cast

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import operator_required
from apps.identity.models import Account
from apps.schedule.models import (
    ChangeRequestStatus,
    ScheduleChangeRequest,
    ScheduleEntry,
)
from apps.schedule.services import (
    approve_change,
    create_entry,
    edit_draft,
    publish_entry,
    reject_change,
    request_change,
    unpublish_entry,
)
from config.api import api

router = Router(auth=operator_required, tags=["operator-schedule"])

_NOTE_MAX = 255


class ScheduleError(Schema):
    """Stable error shape for schedule endpoints."""

    detail: str


class ScheduleEntryOut(Schema):
    """Schedule entry as exposed to operator tools."""

    id: uuid.UUID
    work_date: date_cls
    cast_id: str
    start_time: time
    end_time: time
    status: str
    note: str
    created_at: datetime
    updated_at: datetime


class ScheduleCreateIn(Schema):
    """Operator entry-creation payload."""

    work_date: date_cls
    cast_id: str = Field(max_length=64)
    start_time: time
    end_time: time
    note: str = Field(default="", max_length=_NOTE_MAX)


class ScheduleEditIn(Schema):
    """Draft-only direct edit; omitted fields are unchanged."""

    work_date: date_cls | None = None
    start_time: time | None = None
    end_time: time | None = None
    note: str | None = Field(default=None, max_length=_NOTE_MAX)


class UnpublishIn(Schema):
    """Optional reason when hiding an entry."""

    reason: str = Field(default="", max_length=_NOTE_MAX)


class ChangeRequestIn(Schema):
    """A proposed change to a published entry (work_date/start_time/end_time/note)."""

    proposed: dict[str, str]
    reason: str = Field(default="", max_length=_NOTE_MAX)


class DecisionIn(Schema):
    """Approve/reject decision note."""

    decision_note: str = Field(default="", max_length=_NOTE_MAX)


class ChangeRequestOut(Schema):
    """Schedule change request (the change log row)."""

    id: uuid.UUID
    entry_id: uuid.UUID
    proposed: dict[str, str]
    before: dict[str, str]
    reason: str
    status: str
    requested_by_id: int
    decided_by_id: int | None
    decision_note: str
    created_at: datetime


@router.post("/entries", response={201: ScheduleEntryOut})
def create_entry_endpoint(
    request: HttpRequest, payload: ScheduleCreateIn
) -> tuple[int, ScheduleEntryOut]:
    """Create a draft schedule entry."""
    entry = create_entry(
        work_date=payload.work_date,
        cast_id=payload.cast_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        note=payload.note,
        actor=_actor(request),
    )
    return 201, _entry_out(entry)


@router.get("/entries", response=list[ScheduleEntryOut])
def list_entries(
    request: HttpRequest, date: date_cls | None = None, cast_id: str | None = None
) -> list[ScheduleEntryOut]:
    """List schedule entries (operator sees all statuses)."""
    del request
    qs = ScheduleEntry.objects.all()
    if date is not None:
        qs = qs.filter(work_date=date)
    if cast_id:
        qs = qs.filter(cast_id=cast_id)
    return [_entry_out(e) for e in qs[:500]]


@router.patch(
    "/entries/{entry_id}",
    response={200: ScheduleEntryOut, 400: ScheduleError, 404: ScheduleError},
)
def edit_entry(
    request: HttpRequest, entry_id: uuid.UUID, payload: ScheduleEditIn
) -> tuple[int, ScheduleEntryOut | ScheduleError]:
    """Edit a draft entry directly (published entries require a change request)."""
    entry = get_object_or_404(ScheduleEntry, id=entry_id)
    try:
        edit_draft(
            entry,
            actor=_actor(request),
            work_date=payload.work_date,
            start_time=payload.start_time,
            end_time=payload.end_time,
            note=payload.note,
        )
    except ValueError as exc:
        return 400, ScheduleError(detail=str(exc))
    return 200, _entry_out(entry)


@router.post(
    "/entries/{entry_id}/publish", response={200: ScheduleEntryOut, 404: ScheduleError}
)
def publish_endpoint(
    request: HttpRequest, entry_id: uuid.UUID
) -> tuple[int, ScheduleEntryOut]:
    """Publish an entry."""
    entry = get_object_or_404(ScheduleEntry, id=entry_id)
    publish_entry(entry, actor=_actor(request))
    return 200, _entry_out(entry)


@router.post(
    "/entries/{entry_id}/unpublish",
    response={200: ScheduleEntryOut, 404: ScheduleError},
)
def unpublish_endpoint(
    request: HttpRequest, entry_id: uuid.UUID, payload: UnpublishIn
) -> tuple[int, ScheduleEntryOut]:
    """Hide an entry from fans (비공개)."""
    entry = get_object_or_404(ScheduleEntry, id=entry_id)
    unpublish_entry(entry, actor=_actor(request), reason=payload.reason)
    return 200, _entry_out(entry)


@router.post(
    "/entries/{entry_id}/changes",
    response={201: ChangeRequestOut, 400: ScheduleError, 404: ScheduleError},
)
def request_change_endpoint(
    request: HttpRequest, entry_id: uuid.UUID, payload: ChangeRequestIn
) -> tuple[int, ChangeRequestOut | ScheduleError]:
    """File a pending change to a published entry."""
    entry = get_object_or_404(ScheduleEntry, id=entry_id)
    try:
        change = request_change(
            entry=entry,
            proposed=payload.proposed,
            reason=payload.reason,
            actor=_actor(request),
        )
    except ValueError as exc:
        return 400, ScheduleError(detail=str(exc))
    return 201, _change_out(change)


@router.get("/changes", response={200: list[ChangeRequestOut], 400: ScheduleError})
def list_changes(
    request: HttpRequest, status: str | None = None
) -> tuple[int, list[ChangeRequestOut] | ScheduleError]:
    """List change requests (the schedule change log)."""
    del request
    qs = ScheduleChangeRequest.objects.all()
    if status:
        if status not in ChangeRequestStatus.values:
            return 400, ScheduleError(detail=f"Invalid status: {status}.")
        qs = qs.filter(status=status)
    return 200, [_change_out(c) for c in qs[:500]]


@router.post(
    "/changes/{change_id}/approve",
    response={200: ChangeRequestOut, 400: ScheduleError, 404: ScheduleError},
)
def approve_endpoint(
    request: HttpRequest, change_id: uuid.UUID, payload: DecisionIn
) -> tuple[int, ChangeRequestOut | ScheduleError]:
    """Approve a pending change (must be a different operator than the requester)."""
    change = get_object_or_404(ScheduleChangeRequest, id=change_id)
    try:
        approve_change(
            request=change, actor=_actor(request), decision_note=payload.decision_note
        )
    except ValueError as exc:
        return 400, ScheduleError(detail=str(exc))
    return 200, _change_out(change)


@router.post(
    "/changes/{change_id}/reject",
    response={200: ChangeRequestOut, 400: ScheduleError, 404: ScheduleError},
)
def reject_endpoint(
    request: HttpRequest, change_id: uuid.UUID, payload: DecisionIn
) -> tuple[int, ChangeRequestOut | ScheduleError]:
    """Reject a pending change."""
    change = get_object_or_404(ScheduleChangeRequest, id=change_id)
    try:
        reject_change(
            request=change, actor=_actor(request), decision_note=payload.decision_note
        )
    except ValueError as exc:
        return 400, ScheduleError(detail=str(exc))
    return 200, _change_out(change)


def _actor(request: HttpRequest) -> Account:
    """Return the authenticated operator account supplied by RoleRequired."""
    # request.auth is untyped without Ninja stubs (same idiom as identity/auth.py).
    return cast(Account, request.auth)  # type: ignore[attr-defined]


def _entry_out(entry: ScheduleEntry) -> ScheduleEntryOut:
    """Serialise a schedule entry."""
    return ScheduleEntryOut(
        id=entry.id,
        work_date=entry.work_date,
        cast_id=entry.cast_id,
        start_time=entry.start_time,
        end_time=entry.end_time,
        status=entry.status,
        note=entry.note,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _change_out(change: ScheduleChangeRequest) -> ChangeRequestOut:
    """Serialise a change request (change-log row)."""
    return ChangeRequestOut(
        id=change.id,
        entry_id=change.entry_id,
        proposed=change.proposed,
        before=change.before,
        reason=change.reason,
        status=change.status,
        requested_by_id=change.requested_by_id,
        decided_by_id=change.decided_by_id,
        decision_note=change.decision_note,
        created_at=change.created_at,
    )


api.add_router("/operator/schedule", router)
