"""Rotating QR check-in API (ASS-99).

Two surfaces: a fan asks for a short-lived QR token (`POST /api/checkin/token`),
and an operator redeems a scanned token into a visit
(`POST /api/operator/checkin/redeem`). The token mechanism is the
CONSTRAINTS #18 anti-static-QR control; the on-site flow (store binding, kiosk
vs operator device) is a PRD 열린 확인 사항 layered on top of this primitive.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from django.http import HttpRequest
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import operator_required
from apps.identity.auth import OpaqueTokenAuth, authed
from apps.identity.models import Role
from apps.visit.checkin_services import (
    CheckinThrottled,
    issue_checkin_token,
    redeem_checkin_token,
)
from config.api import api
from config.throttle import user_write_throttle

# Any authenticated account may *ask* for a token; the handler restricts issuance
# to fans (a token is only meaningful as a fan check-in credential).
fan_router = Router(auth=OpaqueTokenAuth(), tags=["checkin"])
operator_router = Router(auth=operator_required, tags=["operator-checkin"])

# A deliberately generous input bound (real tokens are ~43 chars): anything
# longer simply fails the hash lookup as "invalid" — the cap only stops an
# unbounded request body, it is not a correctness check.
_TOKEN_MAX = 128


class CheckinError(Schema):
    """Stable error shape for check-in endpoints."""

    detail: str


class CheckinTokenOut(Schema):
    """A freshly issued rotating check-in token for the fan to render as a QR."""

    token: str
    expires_at: datetime
    ttl_seconds: int


class RedeemIn(Schema):
    """An operator-scanned check-in token.

    No client-supplied store: until an operator→store binding exists, the visit
    uses the default store. A multi-store build will derive the store from the
    operator's association, never from request input (an operator could otherwise
    misattribute a visit to another store).
    """

    token: str = Field(max_length=_TOKEN_MAX)


class RedeemOut(Schema):
    """The visit produced by redeeming a check-in token."""

    visit_id: uuid.UUID
    fan_id: uuid.UUID
    visited_at: datetime
    store_id: str
    checkin_method: str = "qr"


@fan_router.post(
    "/token",
    response={201: CheckinTokenOut, 403: CheckinError, 429: CheckinError},
    throttle=user_write_throttle("30/min"),
)
def issue_token_endpoint(
    request: HttpRequest,
) -> tuple[int, CheckinTokenOut | CheckinError]:
    """Issue a short-lived rotating check-in token for the authenticated fan."""
    account = authed(request)
    if account.role != Role.FAN.value:
        return 403, CheckinError(detail="Only fans can request a check-in QR.")
    try:
        entry, raw = issue_checkin_token(fan=account)
    except CheckinThrottled as exc:
        return 429, CheckinError(detail=str(exc))
    ttl_seconds = int((entry.expires_at - entry.issued_at).total_seconds())
    return 201, CheckinTokenOut(
        token=raw,
        expires_at=entry.expires_at,
        ttl_seconds=ttl_seconds,
    )


@operator_router.post("/redeem", response={200: RedeemOut, 400: CheckinError})
def redeem_token_endpoint(
    request: HttpRequest, payload: RedeemIn
) -> tuple[int, RedeemOut | CheckinError]:
    """Redeem a scanned token into a fan visit (operator scan)."""
    operator = authed(request)
    try:
        record, _token = redeem_checkin_token(
            token=payload.token,
            operator=operator,
        )
    except ValueError as exc:
        return 400, CheckinError(detail=str(exc))
    return 200, RedeemOut(
        visit_id=record.id,
        fan_id=record.fan.fan_id,
        visited_at=record.visited_at,
        store_id=record.store_id,
    )


api.add_router("/checkin", fan_router)
api.add_router("/operator/checkin", operator_router)
