"""Operator + fan API for event campaigns (F10, ASS-107 v0).

- **operator** (``operator_required``): create draft, list/detail (all statuses),
  edit, publish / unpublish / close, and per-campaign reservation list.
- **fan** (``FanBearerAuth`` — bearer only, role-gated): list *published*
  campaigns, record an impression, reserve / waitlist, and list / cancel their
  own reservations. Bearer-only because a state-changing fan POST over the web
  cookie surface needs CSRF (ADR-0002), not yet wired (ASS-110 stance).

Draft campaigns are never exposed to fans (the 승인 전 비공개 gate). No
price/money figure is exposed — the price value is the approval-gated, deferred
slice (issue: "가격·참여 방식 값은 승인 필요").
"""

from __future__ import annotations

import uuid
from datetime import datetime

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import operator_required
from apps.event_campaign.models import (
    CampaignStatus,
    EventCampaign,
    EventReservation,
)
from apps.event_campaign.services import (
    cancel_event_reservation,
    close_campaign,
    create_campaign,
    publish_campaign,
    record_event_view,
    reserve_event,
    unpublish_campaign,
    update_campaign,
)
from apps.identity.auth import FanBearerAuth, authed
from apps.identity.models import Account, Role
from config.api import api
from config.throttle import user_write_throttle

operator_router = Router(auth=operator_required, tags=["operator-event-campaign"])
fan_campaign_router = Router(auth=[FanBearerAuth()], tags=["fan-event-campaign"])
fan_reservation_router = Router(auth=[FanBearerAuth()], tags=["fan-event-reservation"])

_TITLE_MAX = 200
_TEXT_MAX = 2000


class EventCampaignError(Schema):
    """Stable error shape for event-campaign endpoints."""

    detail: str


class CampaignOut(Schema):
    """Campaign fields exposed to operator tools."""

    id: uuid.UUID
    title: str
    description: str
    event_type: str
    cast_id: uuid.UUID | None
    store_id: str
    starts_at: datetime
    ends_at: datetime | None
    notice: str
    status: str
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class FanCampaignOut(Schema):
    """Published-campaign fields exposed to fans (no operator-only data)."""

    id: uuid.UUID
    title: str
    description: str
    event_type: str
    starts_at: datetime
    ends_at: datetime | None
    notice: str
    status: str


class EventReservationOut(Schema):
    """Event reservation row (operator + fan share this shape)."""

    id: uuid.UUID
    campaign_id: uuid.UUID
    status: str
    created_at: datetime


class CampaignCreateIn(Schema):
    """Operator payload to create a draft campaign."""

    title: str = Field(max_length=_TITLE_MAX)
    starts_at: datetime
    event_type: str = "other"
    description: str = Field(default="", max_length=_TEXT_MAX)
    ends_at: datetime | None = None
    notice: str = Field(default="", max_length=_TEXT_MAX)
    cast_id: uuid.UUID | None = None


class CampaignUpdateIn(Schema):
    """Operator change to an open campaign; omitted fields are unchanged."""

    title: str | None = Field(default=None, max_length=_TITLE_MAX)
    description: str | None = Field(default=None, max_length=_TEXT_MAX)
    event_type: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    notice: str | None = Field(default=None, max_length=_TEXT_MAX)


class EventReserveIn(Schema):
    """Fan payload to reserve or waitlist an event."""

    status: str = "reserved"


# --------------------------------------------------------------------------- #
# Operator surface
# --------------------------------------------------------------------------- #
@operator_router.post(
    "", response={201: CampaignOut, 400: EventCampaignError, 404: EventCampaignError}
)
def operator_create_campaign(
    request: HttpRequest,
    payload: CampaignCreateIn,
) -> tuple[int, CampaignOut | EventCampaignError]:
    """Create a draft event campaign."""
    cast_account: Account | None = None
    if payload.cast_id is not None:
        cast_account = get_object_or_404(Account, fan_id=payload.cast_id)
    try:
        campaign = create_campaign(
            actor=_actor(request),
            title=payload.title,
            starts_at=payload.starts_at,
            event_type=payload.event_type,
            description=payload.description,
            ends_at=payload.ends_at,
            notice=payload.notice,
            cast=cast_account,
        )
    except ValueError as exc:
        return 400, EventCampaignError(detail=str(exc))
    return 201, _campaign_out(campaign)


@operator_router.get("", response=list[CampaignOut])
def operator_list_campaigns(
    request: HttpRequest,
    status: str | None = None,
) -> list[CampaignOut]:
    """List campaigns (all statuses), optionally filtered by status."""
    del request
    qs = EventCampaign.objects.all()
    if status:
        qs = qs.filter(status=status)
    return [_campaign_out(c) for c in qs.select_related("cast")]


@operator_router.get("/{campaign_id}", response={200: CampaignOut, 404: EventCampaignError})
def operator_get_campaign(
    request: HttpRequest,
    campaign_id: uuid.UUID,
) -> tuple[int, CampaignOut | EventCampaignError]:
    """Read one campaign (any status)."""
    del request
    campaign = get_object_or_404(EventCampaign, id=campaign_id)
    return 200, _campaign_out(campaign)


@operator_router.post(
    "/{campaign_id}/update",
    response={200: CampaignOut, 400: EventCampaignError, 404: EventCampaignError},
)
def operator_update_campaign(
    request: HttpRequest,
    campaign_id: uuid.UUID,
    payload: CampaignUpdateIn,
) -> tuple[int, CampaignOut | EventCampaignError]:
    """Edit an open campaign."""
    campaign = get_object_or_404(EventCampaign, id=campaign_id)
    try:
        updated = update_campaign(
            campaign=campaign,
            actor=_actor(request),
            title=payload.title,
            description=payload.description,
            event_type=payload.event_type,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            notice=payload.notice,
        )
    except ValueError as exc:
        return 400, EventCampaignError(detail=str(exc))
    return 200, _campaign_out(updated)


@operator_router.post(
    "/{campaign_id}/publish",
    response={200: CampaignOut, 400: EventCampaignError, 404: EventCampaignError},
)
def operator_publish_campaign(
    request: HttpRequest,
    campaign_id: uuid.UUID,
) -> tuple[int, CampaignOut | EventCampaignError]:
    """Publish a draft campaign (now fan-visible)."""
    campaign = get_object_or_404(EventCampaign, id=campaign_id)
    try:
        published = publish_campaign(campaign=campaign, actor=_actor(request))
    except ValueError as exc:
        return 400, EventCampaignError(detail=str(exc))
    return 200, _campaign_out(published)


@operator_router.post(
    "/{campaign_id}/unpublish",
    response={200: CampaignOut, 400: EventCampaignError, 404: EventCampaignError},
)
def operator_unpublish_campaign(
    request: HttpRequest,
    campaign_id: uuid.UUID,
) -> tuple[int, CampaignOut | EventCampaignError]:
    """Return a published campaign to draft (비공개)."""
    campaign = get_object_or_404(EventCampaign, id=campaign_id)
    try:
        drafted = unpublish_campaign(campaign=campaign, actor=_actor(request))
    except ValueError as exc:
        return 400, EventCampaignError(detail=str(exc))
    return 200, _campaign_out(drafted)


@operator_router.post(
    "/{campaign_id}/close",
    response={200: CampaignOut, 400: EventCampaignError, 404: EventCampaignError},
)
def operator_close_campaign(
    request: HttpRequest,
    campaign_id: uuid.UUID,
) -> tuple[int, CampaignOut | EventCampaignError]:
    """Close a campaign (마감)."""
    campaign = get_object_or_404(EventCampaign, id=campaign_id)
    try:
        closed = close_campaign(campaign=campaign, actor=_actor(request))
    except ValueError as exc:
        return 400, EventCampaignError(detail=str(exc))
    return 200, _campaign_out(closed)


@operator_router.get("/{campaign_id}/reservations", response=list[EventReservationOut])
def operator_list_reservations(
    request: HttpRequest,
    campaign_id: uuid.UUID,
) -> list[EventReservationOut]:
    """List reservations for a campaign (operator analysis surface)."""
    del request
    rows = EventReservation.objects.filter(campaign_id=campaign_id)
    return [_reservation_out(r) for r in rows]


# --------------------------------------------------------------------------- #
# Fan surface — campaigns (bearer only; role-gated)
# --------------------------------------------------------------------------- #
@fan_campaign_router.get("", response={200: list[FanCampaignOut], 403: EventCampaignError})
def fan_list_campaigns(
    request: HttpRequest,
) -> tuple[int, list[FanCampaignOut] | EventCampaignError]:
    """List published campaigns (drafts/closed are never shown to fans)."""
    fan = _actor(request)
    if fan.role != Role.FAN.value:
        return 403, EventCampaignError(detail="Only fans can browse events.")
    rows = EventCampaign.objects.filter(status=CampaignStatus.PUBLISHED.value)
    return 200, [_fan_campaign_out(c) for c in rows]


@fan_campaign_router.post(
    "/{campaign_id}/view",
    response={
        200: FanCampaignOut,
        400: EventCampaignError,
        403: EventCampaignError,
        404: EventCampaignError,
    },
    throttle=user_write_throttle("60/min"),
)
def fan_view_campaign(
    request: HttpRequest,
    campaign_id: uuid.UUID,
) -> tuple[int, FanCampaignOut | EventCampaignError]:
    """Record a fan impression of a published campaign and return its detail."""
    fan = _actor(request)
    if fan.role != Role.FAN.value:
        return 403, EventCampaignError(detail="Only fans can view events.")
    # Scope to published so a draft/closed id is a 404, not a 400 (no existence leak).
    campaign = get_object_or_404(
        EventCampaign, id=campaign_id, status=CampaignStatus.PUBLISHED.value
    )
    try:
        record_event_view(campaign=campaign, fan=fan)
    except ValueError as exc:
        return 400, EventCampaignError(detail=str(exc))
    return 200, _fan_campaign_out(campaign)


@fan_campaign_router.post(
    "/{campaign_id}/reserve",
    response={
        201: EventReservationOut,
        400: EventCampaignError,
        403: EventCampaignError,
        404: EventCampaignError,
    },
    throttle=user_write_throttle("20/min"),
)
def fan_reserve_event(
    request: HttpRequest,
    campaign_id: uuid.UUID,
    payload: EventReserveIn,
) -> tuple[int, EventReservationOut | EventCampaignError]:
    """Reserve or waitlist a published campaign for the requesting fan."""
    fan = _actor(request)
    if fan.role != Role.FAN.value:
        return 403, EventCampaignError(detail="Only fans can reserve events.")
    # Scope to published so a draft/closed id is a 404, not a 400 (no existence leak).
    campaign = get_object_or_404(
        EventCampaign, id=campaign_id, status=CampaignStatus.PUBLISHED.value
    )
    try:
        reservation = reserve_event(campaign=campaign, fan=fan, actor=fan, status=payload.status)
    except ValueError as exc:
        return 400, EventCampaignError(detail=str(exc))
    return 201, _reservation_out(reservation)


# --------------------------------------------------------------------------- #
# Fan surface — reservations (bearer only; role-gated)
# --------------------------------------------------------------------------- #
@fan_reservation_router.get("", response={200: list[EventReservationOut], 403: EventCampaignError})
def fan_list_reservations(
    request: HttpRequest,
) -> tuple[int, list[EventReservationOut] | EventCampaignError]:
    """List the requesting fan's own event reservations (all statuses)."""
    fan = _actor(request)
    if fan.role != Role.FAN.value:
        return 403, EventCampaignError(detail="Only fans can view their reservations.")
    rows = EventReservation.objects.filter(fan=fan)
    return 200, [_reservation_out(r) for r in rows]


@fan_reservation_router.post(
    "/{reservation_id}/cancel",
    response={
        200: EventReservationOut,
        400: EventCampaignError,
        403: EventCampaignError,
        404: EventCampaignError,
    },
    throttle=user_write_throttle("20/min"),
)
def fan_cancel_reservation(
    request: HttpRequest,
    reservation_id: uuid.UUID,
) -> tuple[int, EventReservationOut | EventCampaignError]:
    """Cancel one of the requesting fan's own event reservations."""
    fan = _actor(request)
    if fan.role != Role.FAN.value:
        return 403, EventCampaignError(detail="Only fans can cancel their reservations.")
    # Scope by owner so a non-owned id is a 404 (no existence leak).
    reservation = get_object_or_404(EventReservation, id=reservation_id, fan=fan)
    try:
        cancelled = cancel_event_reservation(reservation=reservation, actor=fan)
    except ValueError as exc:
        return 400, EventCampaignError(detail=str(exc))
    return 200, _reservation_out(cancelled)


def _actor(request: HttpRequest) -> Account:
    """Return the authenticated account supplied by the auth class."""
    # request.auth is untyped without Ninja stubs (same idiom as visit/api.py).
    return authed(request)


def _campaign_out(campaign: EventCampaign) -> CampaignOut:
    """Build the operator response schema for a campaign."""
    cast_account = campaign.cast
    return CampaignOut(
        id=campaign.id,
        title=campaign.title,
        description=campaign.description,
        event_type=campaign.event_type,
        cast_id=cast_account.fan_id if cast_account is not None else None,
        store_id=campaign.store_id,
        starts_at=campaign.starts_at,
        ends_at=campaign.ends_at,
        notice=campaign.notice,
        status=campaign.status,
        created_by_id=campaign.created_by_id,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def _fan_campaign_out(campaign: EventCampaign) -> FanCampaignOut:
    """Build the fan-facing response schema (no operator-only fields)."""
    return FanCampaignOut(
        id=campaign.id,
        title=campaign.title,
        description=campaign.description,
        event_type=campaign.event_type,
        starts_at=campaign.starts_at,
        ends_at=campaign.ends_at,
        notice=campaign.notice,
        status=campaign.status,
    )


def _reservation_out(reservation: EventReservation) -> EventReservationOut:
    """Build the response schema for an event reservation."""
    return EventReservationOut(
        id=reservation.id,
        campaign_id=reservation.campaign_id,
        status=reservation.status,
        created_at=reservation.created_at,
    )


api.add_router("/operator/event-campaigns", operator_router)
api.add_router("/fan/event-campaigns", fan_campaign_router)
api.add_router("/fan/event-reservations", fan_reservation_router)
