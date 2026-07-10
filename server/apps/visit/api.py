"""Operator API for manual visit records."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime, time, timedelta

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import operator_required
from apps.identity.auth import authed
from apps.identity.models import Account, Role
from apps.visit.models import VisitRecord
from apps.visit.services import correct_visit, record_visit, void_visit
from config.api import api

router = Router(auth=operator_required, tags=["operator-visits"])


class VisitError(Schema):
    """Stable error shape for operator visit endpoints."""

    detail: str


class VisitRecordOut(Schema):
    """Visit record fields exposed to operator tools without personal data."""

    id: uuid.UUID
    fan_id: uuid.UUID
    visited_at: datetime
    store_id: str
    status: str
    source: str
    note: str
    void_reason: str
    created_by_id: int
    created_at: datetime
    updated_at: datetime


# Bound the operator free-text so a note/reason cannot become an unbounded PII
# sink (an operator could otherwise paste a real name/phone). The note never
# reaches the event log (only note_present: bool is logged); the bound is a
# soft guardrail on the operational row + audit snapshot.
_FREE_TEXT_MAX = 500


class VisitCreateIn(Schema):
    """Payload for operator manual check-in."""

    fan_id: uuid.UUID
    visited_at: datetime | None = None
    note: str = Field(default="", max_length=_FREE_TEXT_MAX)


class VisitPatchIn(Schema):
    """Mutable visit fields; omitted fields are left unchanged."""

    visited_at: datetime | None = None
    note: str | None = Field(default=None, max_length=_FREE_TEXT_MAX)


class VisitVoidIn(Schema):
    """Reason required when voiding a visit record."""

    reason: str = Field(max_length=_FREE_TEXT_MAX)


@router.post("/", response={201: VisitRecordOut, 404: VisitError})
def create_visit(
    request: HttpRequest,
    payload: VisitCreateIn,
) -> tuple[int, VisitRecordOut | VisitError]:
    """Record an operator manual check-in for a fan account."""
    try:
        fan = Account.objects.get(fan_id=payload.fan_id, role=Role.FAN.value)
    except Account.DoesNotExist:
        return 404, VisitError(detail="Fan not found.")

    record = record_visit(
        fan=fan,
        visited_at=payload.visited_at or timezone.now(),
        note=payload.note,
        actor=_actor(request),
    )
    return 201, _record_out(record)


@router.get("/", response=list[VisitRecordOut])
def list_visits(
    request: HttpRequest,
    date: date_type | None = None,
) -> list[VisitRecordOut]:
    """List visits for a business date, including voided records."""
    del request
    day = date or timezone.localdate()
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = start + timedelta(days=1)
    records = (
        VisitRecord.objects.select_related("fan")
        .filter(visited_at__gte=start, visited_at__lt=end)
        .order_by("-visited_at", "-created_at")
    )
    return [_record_out(record) for record in records]


@router.patch(
    "/{record_id}",
    response={200: VisitRecordOut, 404: VisitError},
)
def patch_visit(
    request: HttpRequest,
    record_id: uuid.UUID,
    payload: VisitPatchIn,
) -> tuple[int, VisitRecordOut | VisitError]:
    """Correct the visit timestamp or operator note."""
    record = get_object_or_404(
        VisitRecord.objects.select_related("fan"),
        id=record_id,
    )
    corrected = correct_visit(
        record,
        visited_at=payload.visited_at,
        note=payload.note,
        actor=_actor(request),
    )
    return 200, _record_out(corrected)


@router.post(
    "/{record_id}/void",
    response={200: VisitRecordOut, 400: VisitError, 404: VisitError},
)
def void_visit_endpoint(
    request: HttpRequest,
    record_id: uuid.UUID,
    payload: VisitVoidIn,
) -> tuple[int, VisitRecordOut | VisitError]:
    """Void a visit record with a mandatory operator reason."""
    record = get_object_or_404(
        VisitRecord.objects.select_related("fan"),
        id=record_id,
    )
    try:
        voided = void_visit(record=record, reason=payload.reason, actor=_actor(request))
    except ValueError as exc:
        return 400, VisitError(detail=str(exc))
    return 200, _record_out(voided)


def _actor(request: HttpRequest) -> Account:
    """Return the authenticated operator account supplied by RoleRequired."""
    # Ninja stashes the authenticated principal on request.auth; it is untyped
    # without Ninja stubs, so we ignore attr-defined here (same idiom as
    # identity/auth.py) and cast to the concrete Account.
    return authed(request)


def _record_out(record: VisitRecord) -> VisitRecordOut:
    """Build the response schema without exposing fan personal details."""
    return VisitRecordOut(
        id=record.id,
        fan_id=record.fan.fan_id,
        visited_at=record.visited_at,
        store_id=record.store_id,
        status=record.status,
        source=record.source,
        note=record.note,
        void_reason=record.void_reason,
        created_by_id=record.created_by_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


api.add_router("/operator/visits", router)

# The QR check-in routers (fan token issue + operator redeem) live in their own
# module for separation but are registered here so the visit domain has a single
# api.py entry point (server AGENTS.md router convention).
from apps.visit import checkin_api  # noqa: E402,F401
