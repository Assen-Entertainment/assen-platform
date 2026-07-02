"""Operator API for manual cheki records."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime, time, timedelta
from typing import cast

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import operator_required
from apps.cheki.models import ChekiRecord, ChekiType
from apps.cheki.services import correct_cheki, record_cheki, void_cheki
from apps.identity.models import Account
from apps.visit.models import VisitRecord
from config.api import api

router = Router(auth=operator_required, tags=["operator-cheki"])

_FREE_TEXT_MAX = 500


class ChekiError(Schema):
    """Stable error shape for operator cheki endpoints."""

    detail: str


class ChekiRecordOut(Schema):
    """Cheki record fields exposed to operator tools without personal data."""

    id: uuid.UUID
    visit_id: uuid.UUID
    cast_id: str
    cheki_type: str
    quantity: int
    image_stored: bool
    consent_scope: str
    settlement_status: str
    pos_receipt_no: str
    status: str
    void_reason: str
    created_at: datetime
    updated_at: datetime


class ChekiCreateIn(Schema):
    """Payload for operator cheki record creation."""

    visit_id: uuid.UUID
    cast_id: str = Field(max_length=64)
    cheki_type: str
    quantity: int = Field(ge=1)
    image_stored: bool = False
    # max_length must match the model field (32) so the API is not looser than
    # the DB constraint (a 33-64 char value would pass here then fail at save).
    consent_scope: str = Field(default="", max_length=32)
    pos_receipt_no: str = Field(default="", max_length=64)


class ChekiPatchIn(Schema):
    """Mutable cheki fields; omitted fields are left unchanged."""

    cheki_type: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    consent_scope: str | None = Field(default=None, max_length=32)
    pos_receipt_no: str | None = Field(default=None, max_length=64)


class ChekiVoidIn(Schema):
    """Reason required when voiding a cheki record."""

    reason: str = Field(max_length=_FREE_TEXT_MAX)


def _valid_type(value: str) -> bool:
    """Whether ``value`` is a known cheki type."""
    return value in ChekiType.values


@router.post("/", response={201: ChekiRecordOut, 400: ChekiError, 404: ChekiError})
def create_cheki(
    request: HttpRequest,
    payload: ChekiCreateIn,
) -> tuple[int, ChekiRecordOut | ChekiError]:
    """Record an operator-entered cheki against a visit."""
    if not _valid_type(payload.cheki_type):
        return 400, ChekiError(detail=f"Unknown cheki_type '{payload.cheki_type}'.")
    visit = get_object_or_404(VisitRecord, id=payload.visit_id)
    try:
        record = record_cheki(
            visit=visit,
            cast_id=payload.cast_id,
            cheki_type=payload.cheki_type,
            quantity=payload.quantity,
            image_stored=payload.image_stored,
            consent_scope=payload.consent_scope,
            pos_receipt_no=payload.pos_receipt_no,
            actor=_actor(request),
        )
    except ValueError as exc:
        return 400, ChekiError(detail=str(exc))
    return 201, _record_out(record)


@router.get("/", response=list[ChekiRecordOut])
def list_cheki(
    request: HttpRequest,
    date: date_type | None = None,
    cast_id: str | None = None,
) -> list[ChekiRecordOut]:
    """List cheki records for a day (default today), including voided rows."""
    del request
    day = date or timezone.localdate()
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = start + timedelta(days=1)
    records = ChekiRecord.objects.filter(created_at__gte=start, created_at__lt=end)
    if cast_id:
        records = records.filter(cast_id=cast_id)
    return [_record_out(record) for record in records.order_by("-created_at")]


@router.patch("/{record_id}", response={200: ChekiRecordOut, 400: ChekiError, 404: ChekiError})
def patch_cheki(
    request: HttpRequest,
    record_id: uuid.UUID,
    payload: ChekiPatchIn,
) -> tuple[int, ChekiRecordOut | ChekiError]:
    """Correct cheki metadata (type/quantity/consent/receipt)."""
    if payload.cheki_type is not None and not _valid_type(payload.cheki_type):
        return 400, ChekiError(detail=f"Unknown cheki_type '{payload.cheki_type}'.")
    record = get_object_or_404(ChekiRecord, id=record_id)
    corrected = correct_cheki(
        record,
        cheki_type=payload.cheki_type,
        quantity=payload.quantity,
        consent_scope=payload.consent_scope,
        pos_receipt_no=payload.pos_receipt_no,
        actor=_actor(request),
    )
    return 200, _record_out(corrected)


@router.post(
    "/{record_id}/void",
    response={200: ChekiRecordOut, 400: ChekiError, 404: ChekiError},
)
def void_cheki_endpoint(
    request: HttpRequest,
    record_id: uuid.UUID,
    payload: ChekiVoidIn,
) -> tuple[int, ChekiRecordOut | ChekiError]:
    """Void a cheki record with a mandatory operator reason."""
    record = get_object_or_404(ChekiRecord, id=record_id)
    try:
        voided = void_cheki(record=record, reason=payload.reason, actor=_actor(request))
    except ValueError as exc:
        return 400, ChekiError(detail=str(exc))
    return 200, _record_out(voided)


def _actor(request: HttpRequest) -> Account:
    """Return the authenticated operator account supplied by RoleRequired."""
    # request.auth is untyped without Ninja stubs (same idiom as identity/auth.py).
    return cast(Account, request.auth)  # type: ignore[attr-defined]


def _record_out(record: ChekiRecord) -> ChekiRecordOut:
    """Build the response schema without exposing fan personal details."""
    return ChekiRecordOut(
        id=record.id,
        visit_id=record.visit_id,
        cast_id=record.cast_id,
        cheki_type=record.cheki_type,
        quantity=record.quantity,
        image_stored=record.image_stored,
        consent_scope=record.consent_scope,
        settlement_status=record.settlement_status,
        pos_receipt_no=record.pos_receipt_no,
        status=record.status,
        void_reason=record.void_reason,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


api.add_router("/operator/cheki", router)
