"""Coupon + point API (F09, ASS-108 v0).

- **operator** (``operator_required``): issue / redeem / cancel / expire coupons,
  list coupons, grant / adjust points, and read a fan's point ledger.
- **fan** (``FanBearerAuth`` — bearer only, role-gated): list own coupons and read
  own point balance. Bearer-only because a state-changing fan POST over the web
  cookie surface needs CSRF (ADR-0002), not yet wired (ASS-110 stance); the fan
  surface here is read-only, but kept on the bearer auth for consistency.

No discount/money figure is exposed — the coupon value is the approval-gated,
deferred slice (issue Blocker). #26 비차단 (operator_required / FanBearerAuth reuse,
no token issuance).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import cast

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import operator_required
from apps.coupon.models import Coupon, PointEntry
from apps.coupon.services import (
    adjust_points,
    cancel_coupon,
    expire_coupon,
    grant_points,
    issue_coupon,
    point_balance,
    redeem_coupon,
)
from apps.identity.api import FanBearerAuth
from apps.identity.models import Account, Role
from config.api import api

operator_router = Router(auth=operator_required, tags=["operator-coupon"])
fan_router = Router(auth=[FanBearerAuth()], tags=["fan-coupon"])

_REASON_MAX = 200
_DELTA_MAX = 1_000_000


class CouponError(Schema):
    """Stable error shape for coupon endpoints."""

    detail: str


class CouponOut(Schema):
    """Coupon fields exposed to operator + fan (no money figure)."""

    id: uuid.UUID
    fan_id: uuid.UUID
    coupon_type: str
    status: str
    redemption_id: uuid.UUID | None
    expires_at: datetime | None
    redeemed_at: datetime | None
    created_at: datetime


class PointEntryOut(Schema):
    """One point-ledger row."""

    id: uuid.UUID
    delta: int
    reason: str
    created_at: datetime


class PointBalanceOut(Schema):
    """A fan's point balance + recent ledger entries (operator view, with reason)."""

    fan_id: uuid.UUID
    balance: int
    entries: list[PointEntryOut]


class FanPointEntryOut(Schema):
    """One point-ledger row for the fan (no operator ``reason`` note)."""

    id: uuid.UUID
    delta: int
    created_at: datetime


class FanPointBalanceOut(Schema):
    """The fan's own balance + ledger, omitting the operator-only ``reason``."""

    fan_id: uuid.UUID
    balance: int
    entries: list[FanPointEntryOut]


class CouponIssueIn(Schema):
    """Operator payload to issue a coupon to a fan."""

    fan_id: uuid.UUID
    coupon_type: str
    expires_at: datetime | None = None


class CouponRedeemIn(Schema):
    """Operator payload to redeem a coupon (optional visit reference)."""

    visit_id: str = Field(default="", max_length=64)


class PointMutateIn(Schema):
    """Operator payload to grant or adjust a fan's points.

    ``reference`` is an optional idempotency key: a retry with the same
    ``(fan, reference)`` returns the existing entry instead of double-posting.
    """

    fan_id: uuid.UUID
    delta: int = Field(ge=-_DELTA_MAX, le=_DELTA_MAX)
    reason: str = Field(default="", max_length=_REASON_MAX)
    reference: str = Field(default="", max_length=100)


# --------------------------------------------------------------------------- #
# Operator surface — coupons
# --------------------------------------------------------------------------- #
@operator_router.post("/coupons", response={201: CouponOut, 400: CouponError, 404: CouponError})
def operator_issue_coupon(
    request: HttpRequest, payload: CouponIssueIn
) -> tuple[int, CouponOut | CouponError]:
    """Issue a coupon to a fan."""
    fan = get_object_or_404(Account, fan_id=payload.fan_id)
    try:
        coupon = issue_coupon(
            fan=fan,
            coupon_type=payload.coupon_type,
            actor=_actor(request),
            expires_at=payload.expires_at,
        )
    except ValueError as exc:
        return 400, CouponError(detail=str(exc))
    return 201, _coupon_out(coupon)


@operator_router.get("/coupons", response=list[CouponOut])
def operator_list_coupons(
    request: HttpRequest, fan_id: uuid.UUID | None = None, status: str | None = None
) -> list[CouponOut]:
    """List coupons, optionally filtered by fan and/or status."""
    del request
    qs = Coupon.objects.all()
    if fan_id is not None:
        qs = qs.filter(fan__fan_id=fan_id)
    if status:
        qs = qs.filter(status=status)
    return [_coupon_out(c) for c in qs.select_related("fan")]


@operator_router.post(
    "/coupons/{coupon_id}/redeem",
    response={200: CouponOut, 400: CouponError, 404: CouponError},
)
def operator_redeem_coupon(
    request: HttpRequest, coupon_id: uuid.UUID, payload: CouponRedeemIn
) -> tuple[int, CouponOut | CouponError]:
    """Redeem a coupon (operator, e.g. at POS)."""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    try:
        redeemed = redeem_coupon(coupon=coupon, actor=_actor(request), visit_id=payload.visit_id)
    except ValueError as exc:
        return 400, CouponError(detail=str(exc))
    return 200, _coupon_out(redeemed)


@operator_router.post(
    "/coupons/{coupon_id}/cancel",
    response={200: CouponOut, 400: CouponError, 404: CouponError},
)
def operator_cancel_coupon(
    request: HttpRequest, coupon_id: uuid.UUID
) -> tuple[int, CouponOut | CouponError]:
    """Cancel/void a coupon."""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    try:
        cancelled = cancel_coupon(coupon=coupon, actor=_actor(request))
    except ValueError as exc:
        return 400, CouponError(detail=str(exc))
    return 200, _coupon_out(cancelled)


@operator_router.post(
    "/coupons/{coupon_id}/expire",
    response={200: CouponOut, 400: CouponError, 404: CouponError},
)
def operator_expire_coupon(
    request: HttpRequest, coupon_id: uuid.UUID
) -> tuple[int, CouponOut | CouponError]:
    """Expire an active coupon."""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    try:
        expired = expire_coupon(coupon=coupon, actor=_actor(request))
    except ValueError as exc:
        return 400, CouponError(detail=str(exc))
    return 200, _coupon_out(expired)


# --------------------------------------------------------------------------- #
# Operator surface — points
# --------------------------------------------------------------------------- #
@operator_router.post(
    "/points/grant", response={200: PointEntryOut, 400: CouponError, 404: CouponError}
)
def operator_grant_points(
    request: HttpRequest, payload: PointMutateIn
) -> tuple[int, PointEntryOut | CouponError]:
    """Grant points to a fan."""
    fan = get_object_or_404(Account, fan_id=payload.fan_id)
    try:
        entry = grant_points(
            fan=fan,
            delta=payload.delta,
            actor=_actor(request),
            reason=payload.reason,
            reference=payload.reference,
        )
    except ValueError as exc:
        return 400, CouponError(detail=str(exc))
    return 200, _entry_out(entry)


@operator_router.post(
    "/points/adjust", response={200: PointEntryOut, 400: CouponError, 404: CouponError}
)
def operator_adjust_points(
    request: HttpRequest, payload: PointMutateIn
) -> tuple[int, PointEntryOut | CouponError]:
    """Apply a manual point correction for a fan."""
    fan = get_object_or_404(Account, fan_id=payload.fan_id)
    try:
        entry = adjust_points(
            fan=fan,
            delta=payload.delta,
            actor=_actor(request),
            reason=payload.reason,
            reference=payload.reference,
        )
    except ValueError as exc:
        return 400, CouponError(detail=str(exc))
    return 200, _entry_out(entry)


@operator_router.get("/points/{fan_id}", response={200: PointBalanceOut, 404: CouponError})
def operator_get_points(
    request: HttpRequest, fan_id: uuid.UUID
) -> tuple[int, PointBalanceOut | CouponError]:
    """Read a fan's point balance + ledger (operator)."""
    del request
    fan = get_object_or_404(Account, fan_id=fan_id)
    return 200, _balance_out(fan)


# --------------------------------------------------------------------------- #
# Fan surface (bearer only; role-gated) — read-only
# --------------------------------------------------------------------------- #
@fan_router.get("/coupons", response={200: list[CouponOut], 403: CouponError})
def fan_list_coupons(
    request: HttpRequest,
) -> tuple[int, list[CouponOut] | CouponError]:
    """List the requesting fan's own coupons (all statuses)."""
    fan = _actor(request)
    if fan.role != Role.FAN.value:
        return 403, CouponError(detail="Only fans can view their coupons.")
    return 200, [_coupon_out(c) for c in Coupon.objects.filter(fan=fan)]


@fan_router.get("/points", response={200: FanPointBalanceOut, 403: CouponError})
def fan_get_points(
    request: HttpRequest,
) -> tuple[int, FanPointBalanceOut | CouponError]:
    """Read the requesting fan's own point balance + ledger (no operator reason)."""
    fan = _actor(request)
    if fan.role != Role.FAN.value:
        return 403, CouponError(detail="Only fans can view their points.")
    return 200, _fan_balance_out(fan)


def _actor(request: HttpRequest) -> Account:
    """Return the authenticated account supplied by the auth class."""
    # request.auth is untyped without Ninja stubs (same idiom as visit/api.py).
    return cast(Account, request.auth)  # type: ignore[attr-defined]


def _coupon_out(coupon: Coupon) -> CouponOut:
    """Build the response schema for a coupon."""
    return CouponOut(
        id=coupon.id,
        fan_id=coupon.fan.fan_id,
        coupon_type=coupon.coupon_type,
        status=coupon.status,
        redemption_id=coupon.redemption_id,
        expires_at=coupon.expires_at,
        redeemed_at=coupon.redeemed_at,
        created_at=coupon.created_at,
    )


def _entry_out(entry: PointEntry) -> PointEntryOut:
    """Build the response schema for a point entry."""
    return PointEntryOut(
        id=entry.id, delta=entry.delta, reason=entry.reason, created_at=entry.created_at
    )


def _balance_out(fan: Account) -> PointBalanceOut:
    """Build the operator balance + recent ledger response (includes reason)."""
    entries = [_entry_out(e) for e in PointEntry.objects.filter(fan=fan)[:50]]
    return PointBalanceOut(fan_id=fan.fan_id, balance=point_balance(fan), entries=entries)


def _fan_balance_out(fan: Account) -> FanPointBalanceOut:
    """Build the fan-facing balance + ledger, omitting the operator-only reason."""
    entries = [
        FanPointEntryOut(id=e.id, delta=e.delta, created_at=e.created_at)
        for e in PointEntry.objects.filter(fan=fan)[:50]
    ]
    return FanPointBalanceOut(fan_id=fan.fan_id, balance=point_balance(fan), entries=entries)


api.add_router("/operator/coupon", operator_router)
api.add_router("/fan/coupon", fan_router)
