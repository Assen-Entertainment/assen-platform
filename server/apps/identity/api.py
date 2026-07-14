"""Fan signup, re-auth, session, and digital membership card API (ASS-98 / ASS-237).

Phone-OTP signup + login (mock sender in dev) and the fan session surface. Tokens
are delivered per ADR-0002 by surface: the native app receives them in the JSON
body (and stores them in platform secure storage); the web flow asks for cookies
and receives hardened httpOnly cookies instead, with no secret in the body. The
authenticated endpoints accept either surface — bearer header or the access
cookie — via :data:`fan_auth` (defined in :mod:`apps.identity.auth`).

Endpoints (``/api/fan``):
- ``POST /signup/otp``  — send a (mock) signup OTP.
- ``POST /signup``      — create/attach a fan and issue a token pair.
- ``POST /login``       — re-authenticate an existing fan (phone + OTP).
- ``POST /logout``      — revoke the current token family and clear cookies.
- ``POST /refresh``     — rotate the refresh token (reserved refresh-cookie path).
- ``GET  /me``          — the authenticated fan's identity summary.
- ``PATCH /me``         — update the fan's own profile (nickname).
- ``POST /verify/start``   — begin (mock) 본인인증/성인 인증; fails closed (503) if unwired.
- ``POST /verify/confirm`` — confirm (mock) 본인인증; sets adult_verified / kyc_status.
- ``GET  /csrf``        — issue the ``csrftoken`` cookie for the web double-submit.
- ``GET  /membership-card`` — the authenticated fan's digital membership card.

HUMAN-REVIEW-REQUIRED: auth/identity (CONSTRAINTS #26) — this module issues,
rotates, and revokes tokens, and drives 본인인증(KYC). Raw phone numbers and token
plaintext are never logged; the KYC surface stores only a derived adult flag +
status, never 주민번호/CI/DI/생년월일 원본 (real provider is a 대표·법무 gate —
see :mod:`config.identity_verify`).
"""

from __future__ import annotations

import logging
from datetime import datetime

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from ninja import Router, Schema
from ninja.utils import check_csrf
from pydantic import Field

from apps.consent.models import ConsentKind
from apps.consent.services import marketing_consent_state, record_consent, set_marketing_consent
from apps.identity.auth import access_token_from_request, authed, fan_auth
from apps.identity.cookies import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    clear_auth_cookie,
    set_auth_cookie,
)
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import (
    IssuedTokenPair,
    TokenError,
    issue_token_pair,
    revoke_family_for_access,
    revoke_family_for_refresh,
    rotate_refresh_token,
    withdraw_account,
)
from apps.identity.signup_services import (
    SignupError,
    hash_phone,
    membership_card,
    migrate_legacy_subject_hash,
    normalize_phone,
    register_fan,
)
from config.api import api
from config.errors import ApiError, ErrorCode
from config.identity_verify import identity_verifier
from config.otp import MockOtpSender, OtpSender
from config.throttle import anon_throttle, user_write_throttle

# Auth-failure observability. Structured and strictly PII-free: raw phone numbers
# and token plaintext are NEVER logged (only the failure event + a stable code), so
# the log stream can surface OTP/refresh abuse without leaking an identity.
logger = logging.getLogger(__name__)

# Consent wording version recorded when the fan confirms 성인/본인 인증. Like
# SIGNUP_CONSENT_VERSION, storing the version lets the gate require re-consent when
# the wording changes. Only the consent fact + version persist — never 생년월일.
_KYC_CONSENT_VERSION = "1.0"

# The refresh cookie is scoped to the fan surface. It is deliberately broadened
# from the refresh endpoint alone to the whole ``/api/fan`` prefix (A2): logout
# lives at ``/api/fan/logout`` and must be able to read the refresh cookie to burn
# the family even when the short-lived access cookie has expired. The trade-off is
# a wider send surface for the refresh cookie, accepted because it keeps
# ``SameSite=Strict`` + ``httponly`` (so it is not sent cross-site and is invisible
# to JS) and the one refresh-consuming endpoint (``/refresh``) now enforces CSRF on
# the cookie surface (A3).
_REFRESH_COOKIE_PATH = "/api/fan"


def _otp_sender() -> OtpSender | None:
    """Return the configured OTP sender, or ``None`` when none is wired.

    The deterministic mock is gated behind ``ENABLE_MOCK_FAN_OTP`` (off in
    production) so its reproducible codes can never back a real signup/login. With
    no SMS adapter yet, production returns ``None`` and the surface fails closed
    with 503 rather than trust an unverifiable code (Fan_Signup_Privacy_Policy).

    Runtime caveat (F3): a **new** :class:`MockOtpSender` is built on every call, so
    it carries no armed-code state between the ``/signup/otp`` send and the later
    ``/signup``·``/login`` verify — the verify takes the mock's stateless
    deterministic fallback, which does NOT enforce expiry / single-use / lockout
    (those are proven by unit tests against one shared instance, and are the real
    SMS adapter + shared-store's job, not the mock's). This is not a production
    exposure: prod runs ``ENABLE_MOCK_FAN_OTP=False`` → ``None`` → 503 fail-closed,
    so the un-enforced mock path never executes outside dev/test.
    """
    if settings.ENABLE_MOCK_FAN_OTP:
        return MockOtpSender()
    return None


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
    # 만 14세 이상 확인(D5, 2026-07-12 privacy decisions). Fail-closed default: an
    # omitted field is treated as "not confirmed" → the service rejects with
    # UNDERAGE. The web sends the explicit checkbox value.
    age_over_14: bool = False
    web: bool = False


class LoginIn(Schema):
    """Request body for re-authenticating an existing fan (phone + OTP).

    ``web`` selects cookie delivery exactly like :class:`SignupIn`.
    """

    phone: str
    otp_code: str
    web: bool = False


class RefreshIn(Schema):
    """Request body for token rotation on the app surface.

    The web surface presents the refresh token via the path-scoped httpOnly
    cookie instead, so this field is optional (empty on the cookie surface).
    """

    refresh_token: str = ""


class SignupOut(Schema):
    """Token issuance result. ``token_delivery`` says where the tokens are.

    ``body`` (app): ``access_token``/``refresh_token`` are populated. ``cookie``
    (web): both are empty here and delivered as httpOnly cookies instead, so no
    secret is exposed to browser JS (ADR-0002 XSS defense). Expiries are returned
    either way so the client knows when to refresh. Shared by signup, login, and
    refresh.
    """

    token_delivery: str
    access_token: str = ""
    refresh_token: str = ""
    access_expires_at: datetime
    refresh_expires_at: datetime


class FanMeOut(Schema):
    """The authenticated fan's identity summary (web/app session bootstrap).

    ``handle`` and ``avatar_url`` are populated only when the account operates a
    creator profile (else ``None``); nickname is the sole display PII.
    ``adult_verified`` / ``kyc_status`` are derived 인증 flags (never PII) the web
    session reads to drive 19+ gating and the KYC banner (fail-closed defaults).
    """

    id: str
    nickname: str
    role: str
    handle: str | None = None
    avatar_url: str | None = None
    adult_verified: bool = False
    kyc_status: str = KycStatus.UNVERIFIED.value


class FanMeUpdateIn(Schema):
    """Request body for updating the fan's own profile (nickname only for now).

    Email/phone change is out of this round: both are behind a 본인인증 re-verify
    gate (they key the account's auth), so they are deliberately not editable here.
    """

    nickname: str = Field(min_length=1, max_length=40)


class VerifyConfirmOut(Schema):
    """Result of confirming (mock) 본인인증 — derived flags only, no PII."""

    adult_verified: bool
    kyc_status: str


class MembershipCardOut(Schema):
    """Digital membership card (counts only; nickname is the sole display PII)."""

    nickname: str
    member_id: str
    visit_count: int
    points: int
    coupons: int


class MarketingConsentOut(Schema):
    """A fan's current per-channel marketing opt-in state (D8, optional consent).

    ``email`` is reported for forward compatibility but email is not collected yet,
    so the settings UI shows it disabled and the send path never uses it.
    """

    push: bool
    sms: bool
    email: bool


class MarketingConsentIn(Schema):
    """Desired per-channel marketing opt-in (settings save writes all three)."""

    push: bool
    sms: bool
    email: bool


def _deliver_token_pair(
    pair: IssuedTokenPair, response: HttpResponse, *, web: bool
) -> SignupOut:
    """Deliver an issued token pair by surface (ADR-0002).

    Web asks for cookies: the access cookie is SameSite=Lax so same-site reads
    carry it, and the refresh cookie is SameSite=Strict and path-scoped to the
    refresh endpoint so it is never sent on ordinary reads. ``secure`` is relaxed
    only under DEBUG (local http); production keeps it on. The app surface gets the
    tokens in the body and stores them in secure platform storage. Centralised so
    signup, login, and refresh set identical cookie hardening.
    """
    if web:
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


@router.post("/signup/otp", throttle=anon_throttle("5/min"))
def request_otp(request: HttpRequest, data: OtpRequestIn) -> dict[str, str]:
    """Send (mock) an OTP for the phone. Returns a bare ack — never the code."""
    del request
    sender = _otp_sender()
    if sender is None:
        raise ApiError(
            503,
            "Signup is temporarily unavailable.",
            code=ErrorCode.OTP_UNAVAILABLE,
        )
    try:
        # Canonicalise before send so the code is derived from the same form the
        # signup step verifies against (otherwise a formatted number mismatches).
        phone = normalize_phone(data.phone)
    except SignupError as exc:
        raise ApiError(422, str(exc), code=exc.code) from exc
    sender.send(phone=phone)
    return {"status": "sent"}


@router.post("/signup", response=SignupOut, throttle=anon_throttle("10/min"))
def signup(request: HttpRequest, data: SignupIn, response: HttpResponse) -> SignupOut:
    """Create/attach a fan from a verified OTP + consent; issue a token pair.

    Delivery follows the requested surface (ADR-0002): the web flow gets hardened
    httpOnly cookies (no token in the body); the app gets the tokens in the body.
    """
    del request
    sender = _otp_sender()
    if sender is None:
        raise ApiError(
            503,
            "Signup is temporarily unavailable.",
            code=ErrorCode.OTP_UNAVAILABLE,
        )
    try:
        pair = register_fan(
            phone=data.phone,
            nickname=data.nickname,
            consent_terms=data.consent_terms,
            consent_privacy=data.consent_privacy,
            age_over_14=data.age_over_14,
            otp_code=data.otp_code,
            otp_sender=sender,
        )
    except SignupError as exc:
        raise ApiError(422, str(exc), code=exc.code) from exc

    return _deliver_token_pair(pair, response, web=data.web)


@router.post("/login", response=SignupOut, throttle=anon_throttle("10/min"))
def login(request: HttpRequest, data: LoginIn, response: HttpResponse) -> SignupOut:
    """Re-authenticate an existing fan (phone + OTP) and issue a fresh token pair.

    Disclosure minimisation: the OTP is verified *first*, so "가입이 필요해요" (no
    account) is only ever revealed to a caller who already proved control of the
    phone via a valid code — a wrong code and an unregistered number both look the
    same (422) to anyone else. Delivery follows the requested surface (ADR-0002).
    """
    del request
    sender = _otp_sender()
    if sender is None:
        raise ApiError(
            503, "Login is temporarily unavailable.", code=ErrorCode.OTP_UNAVAILABLE
        )
    try:
        phone = normalize_phone(data.phone)
    except SignupError as exc:
        raise ApiError(422, str(exc), code=exc.code) from exc

    if not sender.verify(phone=phone, code=data.otp_code):
        logger.warning("identity.login.otp_invalid", extra={"code": ErrorCode.OTP_INVALID.value})
        raise ApiError(
            422, "인증번호가 올바르지 않아요.", code=ErrorCode.OTP_INVALID
        )

    # Migrate a pre-A-2 (bare SHA-256) row to the v1 HMAC hash so the lookup below
    # finds it (ASS-287 A-2 dual-read). No-op for accounts already on the v1 hash.
    migrate_legacy_subject_hash(phone)
    account = Account.objects.filter(
        auth_subject_hash=hash_phone(phone),
        role=Role.FAN.value,
        is_active=True,
    ).first()
    if account is None:
        # The number holds no active fan account: guide to signup without exposing
        # more than the caller (who controls the phone) already knows.
        logger.info(
            "identity.login.unregistered",
            extra={"code": ErrorCode.ACCOUNT_NOT_REGISTERED.value},
        )
        raise ApiError(
            422, "가입이 필요해요.", code=ErrorCode.ACCOUNT_NOT_REGISTERED
        )

    return _deliver_token_pair(issue_token_pair(account), response, web=data.web)


@router.post("/logout")
def logout(request: HttpRequest, response: HttpResponse) -> dict[str, str]:
    """Best-effort logout: revoke the session's token family and clear cookies (A2).

    Unauthenticated on purpose. A web session whose short-lived access cookie has
    already expired must still be able to log out using its live refresh cookie, so
    gating this on ``fan_auth`` (which validates the *access* token) would strand
    exactly that case. Instead we revoke off whatever the caller presents: the
    access token (bearer or cookie) and/or the refresh cookie — either burns the
    whole family (F11). Cookie clearing is unconditional so the browser is logged
    out even when no token was presented; the operation is idempotent.

    CSRF: this endpoint is left CSRF-open. A forged cross-site logout can only
    *destroy* a session (revoke tokens + clear cookies), never read data or act as
    the user, so it is a nuisance-level risk accepted for reachability — consistent
    with keeping logout usable from an access-expired web session.
    """
    access = access_token_from_request(request)
    if access is not None:
        revoke_family_for_access(access)
    refresh_cookie = request.COOKIES.get(REFRESH_COOKIE_NAME)
    if refresh_cookie:
        revoke_family_for_refresh(refresh_cookie)
    clear_auth_cookie(response, name=ACCESS_COOKIE_NAME)
    clear_auth_cookie(response, name=REFRESH_COOKIE_NAME, path=_REFRESH_COOKIE_PATH)
    return {"status": "ok"}


@router.post("/refresh", response=SignupOut)
def refresh(
    request: HttpRequest, response: HttpResponse, data: RefreshIn | None = None
) -> SignupOut:
    """Rotate a refresh token and issue a fresh pair; deliver by surface.

    The web surface presents the refresh token via the path-scoped cookie (and
    gets fresh cookies back); the app presents it in the body (and gets a fresh
    body pair). Rotation supersedes the presented token; replay of a consumed
    token revokes the whole family (reuse detection in ``rotate_refresh_token``).
    Any token failure returns a flat 401 that does not distinguish expired vs
    revoked vs reused.

    CSRF (A3): the cookie surface is browser-driven and auto-sends the refresh
    cookie, so this endpoint — which the broadened cookie path (A2) now exposes on
    an unsafe method — verifies the double-submit CSRF token (``/fan/csrf`` cookie
    echoed in ``X-CSRFToken``) whenever the token arrives by cookie. The app/body
    surface presents no cookie and is exempt.
    """
    cookie_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
    web = cookie_token is not None
    if web and check_csrf(request) is not None:
        raise ApiError(403, "CSRF 검증에 실패했어요.", code=ErrorCode.CSRF_FAILED)
    presented = cookie_token or (data.refresh_token if data is not None else None)
    if not presented:
        raise ApiError(
            401, "Refresh token required.", code=ErrorCode.REFRESH_TOKEN_REQUIRED
        )
    try:
        pair = rotate_refresh_token(presented)
    except TokenError as exc:
        logger.warning(
            "identity.refresh.token_invalid",
            extra={
                "code": ErrorCode.REFRESH_TOKEN_INVALID.value,
                "surface": "cookie" if web else "body",
            },
        )
        raise ApiError(
            401, "Refresh token is invalid.", code=ErrorCode.REFRESH_TOKEN_INVALID
        ) from exc
    return _deliver_token_pair(pair, response, web=web)


def _fan_me_out(account: Account) -> FanMeOut:
    """Build the fan identity summary (shared by GET and PATCH ``/me``)."""
    # Lazy import: apps.creator depends on identity, so importing it at module load
    # would create an import cycle. Resolved here per request instead.
    from apps.creator.models import Creator

    creator = Creator.objects.filter(owner=account).first()
    return FanMeOut(
        id=str(account.fan_id),
        nickname=account.nickname,
        role=account.role,
        handle=creator.handle if creator is not None else None,
        avatar_url=creator.avatar_url if creator is not None else None,
        adult_verified=account.adult_verified,
        kyc_status=account.kyc_status,
    )


@router.get("/me", response=FanMeOut, auth=fan_auth)
def get_me(request: HttpRequest) -> FanMeOut:
    """Return the authenticated fan's identity summary (either surface)."""
    return _fan_me_out(authed(request))


@router.patch(
    "/me", response=FanMeOut, auth=fan_auth, throttle=user_write_throttle("6/min")
)
def update_me(request: HttpRequest, data: FanMeUpdateIn) -> FanMeOut:
    """Update the caller's own profile (nickname). Scope is always ``request.auth``.

    The account is taken from the authenticated token, never from the body, so a
    fan can only edit their own profile. nickname is display-only PII (already the
    sole one stored); no new PII is introduced.
    """
    account = authed(request)
    account.nickname = data.nickname
    account.save(update_fields=["nickname"])
    return _fan_me_out(account)


@router.post(
    "/account/withdraw", auth=fan_auth, throttle=user_write_throttle("3/min")
)
def withdraw(request: HttpRequest, response: HttpResponse) -> dict[str, str]:
    """Withdraw (탈퇴) the authenticated fan's account and end the session.

    Privacy decisions 2026-07-12 (D3): anonymises the account in place (clears
    nickname + phone hash, sets is_active False, stamps withdrawn_at) and revokes
    every token family, then clears the web auth cookies so the browser is logged
    out. The scope is always the authenticated account (never the body), so a fan can
    only withdraw their own account. Idempotent at the service layer. Legal-hold
    transaction/dispute records stay linked to the now-pseudonymous fan_id.
    """
    withdraw_account(authed(request))
    clear_auth_cookie(response, name=ACCESS_COOKIE_NAME)
    clear_auth_cookie(response, name=REFRESH_COOKIE_NAME, path=_REFRESH_COOKIE_PATH)
    return {"status": "withdrawn"}


@router.get("/marketing", response=MarketingConsentOut, auth=fan_auth)
def get_marketing(request: HttpRequest) -> MarketingConsentOut:
    """Return the caller's current per-channel marketing opt-in state (D8)."""
    return MarketingConsentOut(**marketing_consent_state(authed(request)))


@router.put(
    "/marketing",
    response=MarketingConsentOut,
    auth=fan_auth,
    throttle=user_write_throttle("12/min"),
)
def set_marketing(request: HttpRequest, data: MarketingConsentIn) -> MarketingConsentOut:
    """Set the caller's per-channel marketing opt-in (settings save, D8).

    Optional consent — any combination (including all-off) is valid and never blocks
    service use. Each channel change appends a durable ConsentRecord audit row. Scope
    is always the authenticated account (never the body).
    """
    account = authed(request)
    set_marketing_consent(account=account, channel="push", enabled=data.push)
    set_marketing_consent(account=account, channel="sms", enabled=data.sms)
    set_marketing_consent(account=account, channel="email", enabled=data.email)
    return MarketingConsentOut(**marketing_consent_state(account))


@router.post(
    "/verify/start", auth=fan_auth, throttle=user_write_throttle("6/min")
)
def verify_start(request: HttpRequest) -> dict[str, str]:
    """Begin (mock) 본인인증/성인 인증 for the authenticated fan.

    Fail-closed: with no verifier wired (``ENABLE_MOCK_KYC`` off / no real provider)
    this returns 503 rather than pretend a challenge started — mirroring the signup
    OTP surface. On success the mock records a ``pending`` transition and returns a
    bare ack (no PII is sent to or received from the mock).
    """
    account = authed(request)
    verifier = identity_verifier()
    if verifier is None:
        raise ApiError(
            503, "본인인증을 사용할 수 없어요.", code=ErrorCode.KYC_UNAVAILABLE
        )
    challenge = verifier.start(account=account)
    # Move an unconfirmed account into 'pending' so the state machine reflects an
    # in-flight challenge; an already-verified account is left as-is (no downgrade).
    if account.kyc_status != KycStatus.VERIFIED.value:
        account.kyc_status = KycStatus.PENDING.value
        account.save(update_fields=["kyc_status"])
    # Expose the provider handshake params when a real adapter returns them, so the
    # client can be redirected / SDK-launched. The mock returns None → the response
    # stays the bare pending ack (byte-identical to before).
    response = {"status": KycStatus.PENDING.value}
    if challenge is not None:
        response["provider"] = challenge.provider
        response["redirect_url"] = challenge.redirect_url
        response["session_id"] = challenge.session_id
    return response


@router.post(
    "/verify/confirm",
    response=VerifyConfirmOut,
    auth=fan_auth,
    throttle=user_write_throttle("6/min"),
)
def verify_confirm(request: HttpRequest) -> VerifyConfirmOut:
    """Confirm (mock) 본인인증 and persist the derived adult flag + status.

    Fail-closed (503) when no verifier is wired. On success the mock returns a
    deterministic adult result; only the derived ``adult_verified`` / ``kyc_status``
    / ``kyc_verified_at`` are written (never 주민번호/CI/DI/생년월일), and the age
    consent is recorded (``ConsentKind.AGE``) so the age-gate has a durable grant.
    No domain event is emitted (AGE consent is not the RULE kind — closed registry).
    """
    account = authed(request)
    verifier = identity_verifier()
    if verifier is None:
        raise ApiError(
            503, "본인인증을 사용할 수 없어요.", code=ErrorCode.KYC_UNAVAILABLE
        )
    result = verifier.confirm(account=account)
    account.adult_verified = result.adult
    account.kyc_status = KycStatus.VERIFIED.value
    account.kyc_verified_at = timezone.now()
    account.save(update_fields=["adult_verified", "kyc_status", "kyc_verified_at"])
    record_consent(
        account=account, kind=ConsentKind.AGE.value, version=_KYC_CONSENT_VERSION
    )
    return VerifyConfirmOut(
        adult_verified=account.adult_verified, kyc_status=account.kyc_status
    )


@router.get("/csrf")
def get_csrf(request: HttpRequest) -> dict[str, str]:
    """Issue the ``csrftoken`` cookie for the web double-submit CSRF defense.

    ``get_token`` marks the request so ``CsrfViewMiddleware`` writes the cookie on
    the way out — the ninja-safe equivalent of ``@ensure_csrf_cookie`` (which can
    only wrap a view returning an ``HttpResponse``, not a serialised dict). The web
    client reads the cookie and echoes it in ``X-CSRFToken`` on unsafe methods.
    """
    get_token(request)
    return {"status": "ok"}


@router.get("/membership-card", response=MembershipCardOut, auth=fan_auth)
def get_membership_card(request: HttpRequest) -> MembershipCardOut:
    """Return the authenticated fan's digital membership card (either surface)."""
    card = membership_card(authed(request))
    return MembershipCardOut(
        nickname=card.nickname,
        member_id=card.member_id,
        visit_count=card.visit_count,
        points=card.points,
        coupons=card.coupons,
    )


api.add_router("/fan", router)
