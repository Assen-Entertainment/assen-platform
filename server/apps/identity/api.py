"""Fan signup, re-auth, session, and digital membership card API (ASS-98 / ASS-237).

Email + social signup/login and the fan session surface. Tokens are delivered per
ADR-0002 by surface: the native app receives them in the JSON body (and stores them
in platform secure storage); the web flow asks for cookies and receives hardened
httpOnly cookies instead, with no secret in the body. The authenticated endpoints
accept either surface — bearer header or the access cookie — via :data:`fan_auth`
(defined in :mod:`apps.identity.auth`).

Endpoints (``/api/fan``):
- ``POST /signup/email`` — create an (unverified) email+password fan; send mock verify mail.
- ``POST /verify-email`` — confirm the email link, mark verified, and issue tokens.
- ``POST /login/email`` — re-authenticate an existing fan (email + password).
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
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from ninja import Router, Schema
from ninja.utils import check_csrf
from pydantic import Field

from apps.consent.models import ConsentKind
from apps.consent.services import marketing_consent_state, record_consent, set_marketing_consent
from apps.consent.versions import consent_doc_version
from apps.identity.auth import access_token_from_request, authed, fan_auth
from apps.identity.cookies import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    SESSION_MARKER_COOKIE_NAME,
    clear_auth_cookie,
    set_auth_cookie,
)
from apps.identity.email_services import (
    EmailVerificationError,
    login_email,
    register_fan_email,
    verify_email,
)
from apps.identity.models import Account, KycStatus
from apps.identity.services import (
    IssuedTokenPair,
    TokenError,
    issue_token_pair,
    revoke_family_for_access,
    revoke_family_for_refresh,
    rotate_refresh_token,
    withdraw_account,
)
from apps.identity.signup_services import SignupError, membership_card
from apps.identity.social_services import (
    make_social_state,
    register_or_login_social,
    verify_social_state,
)
from config.api import api
from config.email import email_sender
from config.errors import ApiError, ErrorCode
from config.identity_verify import identity_verifier
from config.social_auth import (
    SUPPORTED_SOCIAL_PROVIDERS,
    SocialAuthError,
    social_auth_provider,
)
from config.throttle import anon_throttle, user_write_throttle

# Auth-failure observability. Structured and strictly PII-free: raw phone numbers
# and token plaintext are NEVER logged (only the failure event + a stable code), so
# the log stream can surface OTP/refresh abuse without leaking an identity.
logger = logging.getLogger(__name__)

# Consent wording version recorded when the fan confirms 성인/본인 인증. Like the
# signup consent versions (apps.consent.versions), storing the version lets the gate
# require re-consent when the wording changes. This 19+ KYC document carries its own
# version; only the consent fact + version persist — never 생년월일.
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

# Social-login OAuth state cookie: a signed, httpOnly, path-scoped cookie set at
# ``/social/{provider}/start`` and re-verified on ``/callback`` so the callback is bound
# to the browser + provider + redirect_uri that began the flow (anti login-CSRF). The
# signed value is cross-worker safe (no server-side store); see ``social_services``.
SOCIAL_STATE_COOKIE = "assen_social_state"


router = Router(tags=["fan-signup"])


class EmailSignupIn(Schema):
    """Request body for email + password fan signup.

    ``password`` length is validated at the wire (min 8). Consent (terms/privacy + 만
    14세) is mandatory, mirroring social signup. No token is issued here — the fan
    verifies the emailed link first — so there is no ``web`` surface flag.
    """

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=40)
    consent_terms: bool
    consent_privacy: bool
    age_over_14: bool = False
    marketing_consent: bool = False


class EmailSignupOut(Schema):
    """Email-signup ack. Never carries auth tokens (login happens on verify).

    ``verification_token`` is populated only when ``EMAIL_VERIFY_RETURN_TOKEN`` is on
    (dev/test) so e2e can confirm without a real inbox; it is "" on any real surface.
    """

    status: str
    verification_token: str = ""


class VerifyEmailIn(Schema):
    """Request body for confirming an email-verification link.

    ``web`` selects cookie delivery for the token pair issued on verify, exactly like
    :class:`EmailLoginIn`.
    """

    token: str
    web: bool = False


class EmailLoginIn(Schema):
    """Request body for email + password login. ``web`` selects cookie delivery."""

    email: str
    password: str
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
    either way so the client knows when to refresh. Shared by verify-email, email
    login, social callback, and refresh.
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


class ConsentVersionsOut(Schema):
    """Current server-issued version string per presented consent document.

    The (anonymous) signup page reads this before the fan authenticates so it can
    present + echo the exact document versions that get stamped onto each
    ConsentRecord at signup. 법무-게이트: values are placeholders until legal versions
    the copy (single source of truth: apps.consent.versions).
    """

    terms: str
    privacy: str
    age: str


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
        # Non-secret session-presence marker (path="/") — the refresh cookie is scoped
        # to the refresh endpoint, so page routes / Edge middleware never see it and
        # would treat an expired 15-min access cookie as "logged out". This marker (no
        # token, presence only) lives as long as the refresh token so the middleware
        # can tell a refresh session still exists. A broad path is safe: it carries no
        # secret. Raw set_cookie (not set_auth_cookie) — this is not a token cookie.
        response.set_cookie(
            SESSION_MARKER_COOKIE_NAME,
            "1",
            expires=pair.refresh_expires_at,
            httponly=True,
            secure=secure,
            samesite="Lax",
            path="/",
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


class SocialStartOut(Schema):
    """Where to send the client to begin social login (+ the state to echo back)."""

    authorize_url: str
    state: str


class SocialCallbackIn(Schema):
    """Callback body: the provider's authorization ``code`` + first-login consent.

    ``consent_*`` / ``age_over_14`` are enforced only when the social identity is new
    (first login = signup); a returning identity ignores them. ``web`` asks for cookie
    delivery (ADR-0002), matching the email login surface.
    """

    code: str
    state: str = ""
    redirect_uri: str
    consent_terms: bool = False
    consent_privacy: bool = False
    age_over_14: bool = False
    web: bool = False


def _require_supported_provider(provider: str) -> None:
    """Reject an unknown provider path segment (422) before touching the adapter."""
    if provider not in SUPPORTED_SOCIAL_PROVIDERS:
        raise ApiError(
            422,
            "Unsupported social provider.",
            code=ErrorCode.SOCIAL_PROVIDER_UNSUPPORTED,
        )


def _require_allowed_redirect(redirect_uri: str) -> None:
    """Reject a redirect_uri whose origin is not allowlisted (when the allowlist is set).

    Empty allowlist (dev/test default) → skip: the signed state cookie already binds the
    callback to the redirect_uri used at start. Prod configures
    ``SOCIAL_ALLOWED_REDIRECT_ORIGINS`` to lock the surface to known origins.
    """
    allowed = settings.SOCIAL_ALLOWED_REDIRECT_ORIGINS
    if not allowed:
        return
    parts = urlsplit(redirect_uri)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin not in allowed:
        raise ApiError(400, "redirect_uri is not allowed.", code=ErrorCode.SOCIAL_UNAVAILABLE)


@router.get(
    "/social/{provider}/start",
    response=SocialStartOut,
    throttle=anon_throttle("10/min"),
)
def social_start(
    request: HttpRequest, provider: str, redirect_uri: str, response: HttpResponse
) -> SocialStartOut:
    """Begin social login: return the provider consent URL + an opaque state.

    Fails closed (503) when no provider is wired (the mock is gated by
    ENABLE_MOCK_SOCIAL_AUTH), mirroring the OTP/KYC surfaces. The state is echoed to
    the provider AND signed into a path-scoped httpOnly cookie, so the callback can be
    bound to the browser + provider + redirect_uri that started the flow (anti
    login-CSRF); the signed cookie needs no server-side store (cross-worker safe).
    """
    del request
    _require_supported_provider(provider)
    adapter = social_auth_provider()
    if adapter is None:
        raise ApiError(
            503,
            "Social login is temporarily unavailable.",
            code=ErrorCode.SOCIAL_UNAVAILABLE,
        )
    _require_allowed_redirect(redirect_uri)
    state, signed = make_social_state(provider=provider, redirect_uri=redirect_uri)
    authorize_url = adapter.authorize_url(
        provider=provider, state=state, redirect_uri=redirect_uri
    )
    response.set_cookie(
        SOCIAL_STATE_COOKIE,
        signed,
        max_age=settings.SOCIAL_STATE_TTL_SECONDS,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/api/fan",
    )
    return SocialStartOut(authorize_url=authorize_url, state=state)


@router.post(
    "/social/{provider}/callback",
    response=SignupOut,
    throttle=anon_throttle("10/min"),
)
def social_callback(
    request: HttpRequest,
    provider: str,
    data: SocialCallbackIn,
    response: HttpResponse,
) -> SignupOut:
    """Complete social login: exchange the code, then log in / register the fan.

    Delivery follows the requested surface (ADR-0002) — the web flow gets hardened
    httpOnly cookies. A first-time social identity requires terms/privacy + 만 14세
    consent (422 CONSENT_REQUIRED/UNDERAGE if missing); a returning one does not.

    Anti login-CSRF (Codex #7): the signed state cookie set at ``/start`` is re-verified
    against the echoed ``state`` + provider + redirect_uri BEFORE the code exchange, so a
    callback forged by an attacker (no matching cookie, mismatched state, or a swapped
    redirect_uri) is rejected (400) and can never mint tokens into the victim's browser.
    """
    _require_supported_provider(provider)
    adapter = social_auth_provider()
    if adapter is None:
        raise ApiError(
            503,
            "Social login is temporarily unavailable.",
            code=ErrorCode.SOCIAL_UNAVAILABLE,
        )
    _require_allowed_redirect(data.redirect_uri)
    if not verify_social_state(
        cookie_value=request.COOKIES.get(SOCIAL_STATE_COOKIE),
        provider=provider,
        redirect_uri=data.redirect_uri,
        echoed_state=data.state,
    ):
        raise ApiError(
            400,
            "Invalid or expired login state; please retry sign-in.",
            code=ErrorCode.SOCIAL_UNAVAILABLE,
        )
    try:
        profile = adapter.exchange(
            provider=provider, code=data.code, redirect_uri=data.redirect_uri
        )
        pair = register_or_login_social(
            provider=provider,
            subject=profile.subject,
            display_name=profile.display_name,
            consent_terms=data.consent_terms,
            consent_privacy=data.consent_privacy,
            age_over_14=data.age_over_14,
        )
    except SocialAuthError as exc:
        raise ApiError(422, str(exc), code=ErrorCode.SOCIAL_UNAVAILABLE) from exc
    except SignupError as exc:
        raise ApiError(422, str(exc), code=exc.code) from exc
    result = _deliver_token_pair(pair, response, web=data.web)
    # Single-use: consume the state cookie once the flow has completed.
    response.delete_cookie(SOCIAL_STATE_COOKIE, path="/api/fan")
    return result


@router.post("/signup/email", response=EmailSignupOut, throttle=anon_throttle("10/min"))
def signup_email(request: HttpRequest, data: EmailSignupIn) -> EmailSignupOut:
    """Create an (unverified) email + password fan and send a mock verification mail.

    Fails closed (503) when no email sender is wired (the mock is gated by
    ``ENABLE_MOCK_EMAIL``, off in production), mirroring the social surface. No token is
    issued — the fan is logged in on ``/verify-email``. A duplicate verified email is
    409; consent/age/password-length failures are 422. The verification token is
    echoed only under the ``EMAIL_VERIFY_RETURN_TOKEN`` dev flag (else "").
    """
    del request
    sender = email_sender()
    if sender is None:
        raise ApiError(
            503,
            "이메일 가입을 사용할 수 없어요.",
            code=ErrorCode.EMAIL_UNAVAILABLE,
        )
    try:
        _account, token = register_fan_email(
            email=data.email,
            password=data.password,
            nickname=data.nickname,
            consent_terms=data.consent_terms,
            consent_privacy=data.consent_privacy,
            age_over_14=data.age_over_14,
            marketing_consent=data.marketing_consent,
            email_sender=sender,
        )
    except SignupError as exc:
        status = 409 if exc.code == ErrorCode.EMAIL_ALREADY_REGISTERED else 422
        raise ApiError(status, str(exc), code=exc.code) from exc
    return EmailSignupOut(
        status="verification_sent",
        verification_token=token if settings.EMAIL_VERIFY_RETURN_TOKEN else "",
    )


@router.post("/verify-email", response=SignupOut, throttle=anon_throttle("10/min"))
def verify_email_endpoint(
    request: HttpRequest, data: VerifyEmailIn, response: HttpResponse
) -> SignupOut:
    """Confirm an email-verification token, mark the account verified, and log in.

    On the first valid confirm the account is marked verified and a token pair is
    issued + delivered by surface (ADR-0002); a forged/expired/mismatched token is 400.
    """
    del request
    try:
        pair = verify_email(token=data.token)
    except EmailVerificationError as exc:
        raise ApiError(
            400, "인증 링크가 유효하지 않거나 만료됐어요.",
            code=ErrorCode.EMAIL_VERIFICATION_INVALID,
        ) from exc
    return _deliver_token_pair(pair, response, web=data.web)


@router.post("/login/email", response=SignupOut, throttle=anon_throttle("10/min"))
def login_email_endpoint(
    request: HttpRequest, data: EmailLoginIn, response: HttpResponse
) -> SignupOut:
    """Authenticate an email + password fan and issue a fresh token pair.

    Disclosure-safe: a wrong email and a wrong password are indistinguishable (422
    ``InvalidCredentials``). A correct password on an unverified account is 403
    ``EMAIL_NOT_VERIFIED`` (verification is required before login). Delivery follows
    the requested surface (ADR-0002).
    """
    del request
    try:
        account = login_email(email=data.email, password=data.password)
    except SignupError as exc:
        status = 403 if exc.code == ErrorCode.EMAIL_NOT_VERIFIED else 422
        raise ApiError(status, str(exc), code=exc.code) from exc
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
    response.delete_cookie(SESSION_MARKER_COOKIE_NAME, path="/")
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
    nickname + phone hash, sets is_active False, stamps withdrawn_at), offboards the
    fan (cancels active subscriptions, unpublishes any creator storefront, pseudonymises
    comment author snapshots — Codex #13) and revokes every token family, then clears
    the web auth cookies so the browser is logged out. The scope is always the
    authenticated account (never the body), so a fan can only withdraw their own
    account. Idempotent at the service layer. Legal-hold transaction/dispute records
    stay linked to the now-pseudonymous fan_id.

    Staff guard (Codex #13): a staff account (operator/manager/admin/system) is refused
    here (403 ``StaffWithdrawalForbidden``) — staff offboarding is a separate ops flow,
    so the last-admin invariant can never be broken through fan self-service. Regular
    fans (including creators, who are fans operating a creator page) proceed.
    """
    account = authed(request)
    if account.is_operator_account:
        raise ApiError(
            403,
            "관리자 계정은 이 화면에서 탈퇴할 수 없어요. 운영 오프보딩 절차를 이용해 주세요.",
            code=ErrorCode.STAFF_WITHDRAWAL_FORBIDDEN,
        )
    withdraw_account(account)
    clear_auth_cookie(response, name=ACCESS_COOKIE_NAME)
    clear_auth_cookie(response, name=REFRESH_COOKIE_NAME, path=_REFRESH_COOKIE_PATH)
    response.delete_cookie(SESSION_MARKER_COOKIE_NAME, path="/")
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


@router.get("/consent/versions", response=ConsentVersionsOut)
def get_consent_versions(request: HttpRequest) -> ConsentVersionsOut:
    """Return the current presented version of each consent document (anonymous).

    Anonymous by design: the signup page runs before auth and reads this to present +
    echo the exact terms/privacy/age document versions recorded onto each
    ConsentRecord at signup. Values come from the single source of truth
    (apps.consent.versions — 법무-게이트: placeholders until legal versions the copy).
    """
    del request
    return ConsentVersionsOut(
        terms=consent_doc_version(ConsentKind.TERMS.value),
        privacy=consent_doc_version(ConsentKind.PRIVACY.value),
        age=consent_doc_version(ConsentKind.AGE.value),
    )


@router.post(
    "/verify/start", auth=fan_auth, throttle=user_write_throttle("6/min")
)
def verify_start(request: HttpRequest) -> dict[str, str]:
    """Begin (mock) 본인인증/성인 인증 for the authenticated fan.

    Fail-closed: with no verifier wired (``ENABLE_MOCK_KYC`` off / no real provider)
    this returns 503 rather than pretend a challenge started — mirroring the email
    signup surface. On success the mock records a ``pending`` transition and returns a
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
