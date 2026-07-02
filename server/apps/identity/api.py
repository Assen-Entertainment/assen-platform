"""Fan signup + digital membership card API (ASS-98 v0).

Phone-OTP signup (mock sender in P0) and the membership-card read endpoint.
Tokens are delivered per ADR-0002 by surface: the native app receives them in
the JSON body (and stores them in platform secure storage); the web flow asks
for cookies and receives hardened httpOnly cookies instead, with no secret in
the body. The card endpoint authenticates either surface — bearer header or the
access cookie — via :data:`fan_auth`.

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26) — this endpoint issues tokens.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import APIKeyCookie, HttpBearer
from pydantic import Field

from apps.identity.cookies import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    set_auth_cookie,
)
from apps.identity.models import Account
from apps.identity.services import TokenError, verify_access_token
from apps.identity.signup_services import (
    SignupError,
    membership_card,
    normalize_phone,
    register_fan,
)
from config.api import api
from config.otp import MockOtpSender, OtpSender

# The refresh cookie is scoped to the (future) refresh endpoint so it is never
# sent on ordinary authenticated reads — only the short-lived access cookie is.
_REFRESH_COOKIE_PATH = "/api/fan/refresh"


def _otp_sender() -> OtpSender | None:
    """Return the configured OTP sender, or ``None`` when none is wired.

    The deterministic mock is gated behind ``ENABLE_MOCK_FAN_OTP`` (off in
    production) so its reproducible codes can never back a real signup. With no
    SMS adapter yet, production returns ``None`` and the signup surface fails
    closed with 503 rather than trust an unverifiable code
    (Fan_Signup_Privacy_Policy §1, §8).
    """
    if settings.ENABLE_MOCK_FAN_OTP:
        return MockOtpSender()
    return None


def _authenticate(request: HttpRequest, token: str) -> Account | None:
    """Resolve a token to its account (shared by both auth surfaces)."""
    try:
        account = verify_access_token(token)
    except TokenError:
        return None
    request.account = account  # type: ignore[attr-defined]
    return account


class FanBearerAuth(HttpBearer):
    """App surface: authenticate ``Authorization: Bearer <access token>``."""

    def authenticate(self, request: HttpRequest, token: str) -> Account | None:
        """Return the account for a valid bearer token, else None (→ 401)."""
        return _authenticate(request, token)


class FanCookieAuth(APIKeyCookie):
    """Web surface: authenticate the httpOnly ``assen_access`` cookie."""

    param_name = ACCESS_COOKIE_NAME

    def authenticate(self, request: HttpRequest, key: str | None) -> Account | None:
        """Return the account for a valid access cookie, else None (→ 401)."""
        if not key:
            return None
        return _authenticate(request, key)


# Role-agnostic authentication for the fan surface: try the app bearer token
# first, then the web access cookie. Either one proves the caller owns the token;
# the card endpoint returns only the caller's own data, so no staff role is
# required (mirrors the prior authenticate-only design).
fan_auth = [FanBearerAuth(), FanCookieAuth()]
router = Router(tags=["fan-signup"])


class OtpRequestIn(Schema):
    """Request body for sending a signup OTP."""

    phone: str


class SignupIn(Schema):
    """Request body for completing fan signup.

    ``web`` lets the web flow ask for cookie delivery (ADR-0002): when true the
    tokens are set as hardened httpOnly cookies and omitted from the body.
    """

    phone: str
    otp_code: str
    nickname: str = Field(min_length=1, max_length=40)
    consent_terms: bool
    consent_privacy: bool
    web: bool = False


class SignupOut(Schema):
    """Signup result. ``token_delivery`` says where the tokens are.

    ``body`` (app): ``access_token``/``refresh_token`` are populated. ``cookie``
    (web): both are empty here and delivered as httpOnly cookies instead, so no
    secret is exposed to browser JS (ADR-0002 XSS defense). Expiries are returned
    either way so the client knows when to refresh.
    """

    token_delivery: str
    access_token: str = ""
    refresh_token: str = ""
    access_expires_at: datetime
    refresh_expires_at: datetime


class MembershipCardOut(Schema):
    """Digital membership card (counts only; nickname is the sole display PII)."""

    nickname: str
    member_id: str
    visit_count: int
    points: int
    coupons: int


@router.post("/signup/otp")
def request_otp(request: HttpRequest, data: OtpRequestIn) -> dict[str, str]:
    """Send (mock) an OTP for the phone. Returns a bare ack — never the code."""
    del request
    sender = _otp_sender()
    if sender is None:
        raise HttpError(503, "Signup is temporarily unavailable.")
    try:
        # Canonicalise before send so the code is derived from the same form the
        # signup step verifies against (otherwise a formatted number mismatches).
        phone = normalize_phone(data.phone)
    except SignupError as exc:
        raise HttpError(422, str(exc)) from exc
    sender.send(phone=phone)
    return {"status": "sent"}


@router.post("/signup", response=SignupOut)
def signup(request: HttpRequest, data: SignupIn, response: HttpResponse) -> SignupOut:
    """Create/attach a fan from a verified OTP + consent; issue a token pair.

    Delivery follows the requested surface (ADR-0002): the web flow gets hardened
    httpOnly cookies (no token in the body); the app gets the tokens in the body.
    """
    del request
    sender = _otp_sender()
    if sender is None:
        raise HttpError(503, "Signup is temporarily unavailable.")
    try:
        pair = register_fan(
            phone=data.phone,
            nickname=data.nickname,
            consent_terms=data.consent_terms,
            consent_privacy=data.consent_privacy,
            otp_code=data.otp_code,
            otp_sender=sender,
        )
    except SignupError as exc:
        raise HttpError(422, str(exc)) from exc

    if data.web:
        # secure is relaxed only under DEBUG (local http); production keeps it on.
        # The refresh cookie is SameSite=Strict and path-scoped to the refresh
        # endpoint; the access cookie is Lax so same-site reads carry it. No
        # authenticated state-changing fan endpoint exists in v0, so double-submit
        # CSRF enforcement attaches with the first one — httpOnly + SameSite guard
        # the cookies meanwhile.
        secure = not settings.DEBUG
        set_auth_cookie(
            response,
            name=ACCESS_COOKIE_NAME,
            value=pair.access_token,
            expires_at=pair.access_expires_at,
            secure=secure,
            samesite="Lax",
        )
        set_auth_cookie(
            response,
            name=REFRESH_COOKIE_NAME,
            value=pair.refresh_token,
            expires_at=pair.refresh_expires_at,
            secure=secure,
            samesite="Strict",
            path=_REFRESH_COOKIE_PATH,
        )
        return SignupOut(
            token_delivery="cookie",
            access_expires_at=pair.access_expires_at,
            refresh_expires_at=pair.refresh_expires_at,
        )

    return SignupOut(
        token_delivery="body",
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        access_expires_at=pair.access_expires_at,
        refresh_expires_at=pair.refresh_expires_at,
    )


@router.get("/membership-card", response=MembershipCardOut, auth=fan_auth)
def get_membership_card(request: HttpRequest) -> MembershipCardOut:
    """Return the authenticated fan's digital membership card (either surface)."""
    card = membership_card(cast(Account, request.auth))  # type: ignore[attr-defined]
    return MembershipCardOut(
        nickname=card.nickname,
        member_id=card.member_id,
        visit_count=card.visit_count,
        points=card.points,
        coupons=card.coupons,
    )


api.add_router("/fan", router)
