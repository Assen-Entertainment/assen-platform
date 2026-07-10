"""Operator + fan API for reservation/waitlist (F03, ASS-109 v0).

Two surfaces share the reservation service:

- **operator** (``operator_required``): create on a fan's behalf, the day's
  reservation/waitlist list, and the approve/change/cancel/no-show lifecycle.
- **fan** (``FanBearerAuth`` — bearer only): a fan registers and lists/cancels
  *their own* reservations. Bearer-only because a state-changing fan POST over
  the web cookie surface needs CSRF (ADR-0002), which is not yet wired — same
  stance as the fan safety-report endpoint (ASS-110).

``fan_auth`` is role-agnostic, so the fan endpoints additionally gate
``role == fan`` (a staff token must not file fan-attributed reservations).
External-store / 네이버 예약 sync, prepaid, and seat assignment are out of v0.
"""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime, time

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import operator_required
from apps.identity.auth import FanBearerAuth, authed
from apps.identity.models import Account, Role
from apps.reservation.models import Reservation
from apps.reservation.services import (
    cancel_reservation,
    change_reservation,
    confirm_reservation,
    create_reservation,
    mark_no_show,
)
from config.api import api
from config.throttle import user_write_throttle

operator_router = Router(auth=operator_required, tags=["operator-reservation"])
fan_router = Router(auth=[FanBearerAuth()], tags=["fan-reservation"])

_NOTE_MAX = 500
_PARTY_MAX = 20


class ReservationError(Schema):
    """Stable error shape for reservation endpoints."""

    detail: str


class ReservationOut(Schema):
    """Reservation fields exposed to operator tools."""

    id: uuid.UUID
    fan_id: uuid.UUID
    store_id: str
    reservation_type: str
    status: str
    reserved_date: date_type
    reserved_time: time | None
    party_size: int
    operator_note: str
    cancellation_reason: str
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class FanReservationOut(Schema):
    """Reservation fields exposed to the owning fan (no operator-only data)."""

    id: uuid.UUID
    reservation_type: str
    status: str
    reserved_date: date_type
    reserved_time: time | None
    party_size: int
    created_at: datetime


class ReservationCreateIn(Schema):
    """Operator payload to record a reservation on a fan's behalf."""

    fan_id: uuid.UUID
    reserved_date: date_type
    reserved_time: time | None = None
    party_size: int = Field(default=1, ge=1, le=_PARTY_MAX)
    reservation_type: str = "reservation"
    operator_note: str = Field(default="", max_length=_NOTE_MAX)


class FanReservationCreateIn(Schema):
    """Fan payload to register their own reservation/waitlist entry."""

    reserved_date: date_type
    reserved_time: time | None = None
    party_size: int = Field(default=1, ge=1, le=_PARTY_MAX)
    reservation_type: str = "reservation"


class ReservationChangeIn(Schema):
    """Operator change to an active reservation; omitted fields are unchanged."""

    reserved_date: date_type | None = None
    reserved_time: time | None = None
    party_size: int | None = Field(default=None, ge=1, le=_PARTY_MAX)


class ReservationReasonIn(Schema):
    """Optional operational reason for a cancel / no-show."""

    reason: str = Field(default="", max_length=_NOTE_MAX)


# --------------------------------------------------------------------------- #
# Operator surface
# --------------------------------------------------------------------------- #
@operator_router.post(
    "", response={201: ReservationOut, 400: ReservationError, 404: ReservationError},
    throttle=user_write_throttle("60/min"),
)
def operator_create_reservation(
    request: HttpRequest,
    payload: ReservationCreateIn,
) -> tuple[int, ReservationOut | ReservationError]:
    """Record a reservation/waitlist entry for a fan."""
    fan = get_object_or_404(Account, fan_id=payload.fan_id)
    try:
        reservation = create_reservation(
            fan=fan,
            actor=_actor(request),
            reserved_date=payload.reserved_date,
            reserved_time=payload.reserved_time,
            party_size=payload.party_size,
            reservation_type=payload.reservation_type,
            operator_note=payload.operator_note,
        )
    except ValueError as exc:
        return 400, ReservationError(detail=str(exc))
    return 201, _out(reservation)


@operator_router.get("", response=list[ReservationOut])
def operator_list_reservations(
    request: HttpRequest,
    date: date_type | None = None,
) -> list[ReservationOut]:
    """List reservations for a reserved date (default today), all statuses."""
    del request
    day = date or timezone.localdate()
    records = (
        Reservation.objects.filter(reserved_date=day)
        .select_related("fan")
        .order_by("reserved_time", "-created_at")
    )
    return [_out(record) for record in records]


@operator_router.post(
    "/{reservation_id}/confirm",
    response={200: ReservationOut, 400: ReservationError, 404: ReservationError},
    throttle=user_write_throttle("60/min"),
)
def operator_confirm_reservation(
    request: HttpRequest,
    reservation_id: uuid.UUID,
) -> tuple[int, ReservationOut | ReservationError]:
    """Approve a requested reservation."""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    try:
        confirmed = confirm_reservation(reservation=reservation, actor=_actor(request))
    except ValueError as exc:
        return 400, ReservationError(detail=str(exc))
    return 200, _out(confirmed)


@operator_router.post(
    "/{reservation_id}/change",
    response={200: ReservationOut, 400: ReservationError, 404: ReservationError},
    throttle=user_write_throttle("60/min"),
)
def operator_change_reservation(
    request: HttpRequest,
    reservation_id: uuid.UUID,
    payload: ReservationChangeIn,
) -> tuple[int, ReservationOut | ReservationError]:
    """Change the slot of an active reservation."""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    try:
        changed = change_reservation(
            reservation=reservation,
            actor=_actor(request),
            reserved_date=payload.reserved_date,
            reserved_time=payload.reserved_time,
            party_size=payload.party_size,
        )
    except ValueError as exc:
        return 400, ReservationError(detail=str(exc))
    return 200, _out(changed)


@operator_router.post(
    "/{reservation_id}/cancel",
    response={200: ReservationOut, 400: ReservationError, 404: ReservationError},
    throttle=user_write_throttle("60/min"),
)
def operator_cancel_reservation(
    request: HttpRequest,
    reservation_id: uuid.UUID,
    payload: ReservationReasonIn,
) -> tuple[int, ReservationOut | ReservationError]:
    """Cancel an active reservation (operator)."""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    try:
        cancelled = cancel_reservation(
            reservation=reservation, actor=_actor(request), reason=payload.reason
        )
    except ValueError as exc:
        return 400, ReservationError(detail=str(exc))
    return 200, _out(cancelled)


@operator_router.post(
    "/{reservation_id}/no-show",
    response={200: ReservationOut, 400: ReservationError, 404: ReservationError},
    throttle=user_write_throttle("60/min"),
)
def operator_no_show_reservation(
    request: HttpRequest,
    reservation_id: uuid.UUID,
    payload: ReservationReasonIn,
) -> tuple[int, ReservationOut | ReservationError]:
    """Record a no-show for an active reservation."""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    try:
        no_show = mark_no_show(
            reservation=reservation, actor=_actor(request), reason=payload.reason
        )
    except ValueError as exc:
        return 400, ReservationError(detail=str(exc))
    return 200, _out(no_show)


# --------------------------------------------------------------------------- #
# Fan surface (bearer only; role-gated to fans)
# --------------------------------------------------------------------------- #
@fan_router.post(
    "", response={201: FanReservationOut, 400: ReservationError, 403: ReservationError},
    throttle=user_write_throttle("20/min"),
)
def fan_create_reservation(
    request: HttpRequest,
    payload: FanReservationCreateIn,
) -> tuple[int, FanReservationOut | ReservationError]:
    """Register the requesting fan's own reservation/waitlist entry."""
    fan = _actor(request)
    if fan.role != Role.FAN.value:
        return 403, ReservationError(detail="Only fans can register their own reservations.")
    try:
        reservation = create_reservation(
            fan=fan,
            actor=fan,
            reserved_date=payload.reserved_date,
            reserved_time=payload.reserved_time,
            party_size=payload.party_size,
            reservation_type=payload.reservation_type,
        )
    except ValueError as exc:
        return 400, ReservationError(detail=str(exc))
    return 201, _fan_out(reservation)


@fan_router.get("", response={200: list[FanReservationOut], 403: ReservationError})
def fan_list_reservations(
    request: HttpRequest,
) -> tuple[int, list[FanReservationOut] | ReservationError]:
    """List the requesting fan's own reservations (all statuses)."""
    fan = _actor(request)
    if fan.role != Role.FAN.value:
        return 403, ReservationError(detail="Only fans can view their own reservations.")
    records: QuerySet[Reservation] = Reservation.objects.filter(fan=fan).order_by("-created_at")
    return 200, [_fan_out(record) for record in records]


@fan_router.post(
    "/{reservation_id}/cancel",
    response={
        200: FanReservationOut,
        400: ReservationError,
        403: ReservationError,
        404: ReservationError,
    },
    throttle=user_write_throttle("20/min"),
)
def fan_cancel_reservation(
    request: HttpRequest,
    reservation_id: uuid.UUID,
) -> tuple[int, FanReservationOut | ReservationError]:
    """Cancel one of the requesting fan's own reservations.

    No reason is accepted from the fan: free text here would store fan PII in the
    operational trail (ASS-110). Only operators supply a cancellation reason.
    """
    fan = _actor(request)
    if fan.role != Role.FAN.value:
        return 403, ReservationError(detail="Only fans can cancel their own reservations.")
    # Scope by owner so a non-owned id is a 404 (no existence leak).
    reservation = get_object_or_404(Reservation, id=reservation_id, fan=fan)
    try:
        cancelled = cancel_reservation(reservation=reservation, actor=fan)
    except ValueError as exc:
        return 400, ReservationError(detail=str(exc))
    return 200, _fan_out(cancelled)


def _actor(request: HttpRequest) -> Account:
    """Return the authenticated account supplied by the auth class."""
    # request.auth is untyped without Ninja stubs (same idiom as visit/api.py).
    return authed(request)


def _out(record: Reservation) -> ReservationOut:
    """Build the operator response schema for a reservation."""
    return ReservationOut(
        id=record.id,
        fan_id=record.fan.fan_id,
        store_id=record.store_id,
        reservation_type=record.reservation_type,
        status=record.status,
        reserved_date=record.reserved_date,
        reserved_time=record.reserved_time,
        party_size=record.party_size,
        operator_note=record.operator_note,
        cancellation_reason=record.cancellation_reason,
        created_by_id=record.created_by_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _fan_out(record: Reservation) -> FanReservationOut:
    """Build the fan-facing response schema (no operator-only fields)."""
    return FanReservationOut(
        id=record.id,
        reservation_type=record.reservation_type,
        status=record.status,
        reserved_date=record.reserved_date,
        reserved_time=record.reserved_time,
        party_size=record.party_size,
        created_at=record.created_at,
    )


api.add_router("/operator/reservations", operator_router)
api.add_router("/fan/reservations", fan_router)
