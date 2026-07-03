"""Tests for the fan re-auth / session endpoints (ASS-237).

Covers login (body + cookie surfaces, unregistered, bad OTP), logout revocation +
cookie clearing, refresh rotation + reuse detection, the ``/me`` contract, the
``/csrf`` cookie, and the ``resolve_optional_account`` helper. The guard promotion
into :mod:`apps.identity.auth` is exercised implicitly by every authenticated call
here and by the untouched signup/card suite (``test_signup.py``).

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.core.cache import cache
from django.test import Client, RequestFactory
from ninja.throttling import AnonRateThrottle

from apps.creator.models import Creator
from apps.identity.auth import resolve_optional_account
from apps.identity.cookies import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from apps.identity.models import Account, RefreshToken, Role
from apps.identity.services import hash_token, issue_token_pair
from apps.identity.signup_services import hash_phone, register_fan
from config.api import api
from config.otp import MockOtpSender

pytestmark = pytest.mark.django_db

_SENDER = MockOtpSender()
_PHONE = "+821012345678"


def _code(phone: str = _PHONE) -> str:
    return _SENDER.code_for(phone)


def _wrong_code(phone: str = _PHONE) -> str:
    good = _code(phone)
    return "654321" if good != "654321" else "123456"


def _register(phone: str = _PHONE, nickname: str = "미오팬") -> Account:
    register_fan(
        phone=phone,
        nickname=nickname,
        consent_terms=True,
        consent_privacy=True,
        otp_code=_code(phone),
        otp_sender=_SENDER,
    )
    return Account.objects.get(auth_subject_hash=hash_phone(phone))


def _post(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.post(
        path, data=json.dumps(body), content_type="application/json", **extra
    )


def _bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


# --- login -------------------------------------------------------------------


def test_login_returns_tokens_in_body(client: Client) -> None:
    _register()
    resp = _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code()})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_delivery"] == "body"
    assert body["access_token"] and body["refresh_token"]
    # The app surface sets no auth cookies (tokens go to secure platform storage).
    assert ACCESS_COOKIE_NAME not in client.cookies


def test_login_web_sets_httponly_cookies_not_body(client: Client) -> None:
    _register()
    resp = _post(
        client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code(), "web": True}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_delivery"] == "cookie"
    assert body["access_token"] == "" and body["refresh_token"] == ""
    access = client.cookies[ACCESS_COOKIE_NAME]
    assert access["httponly"]
    assert access["samesite"].lower() == "lax"
    refresh = client.cookies[REFRESH_COOKIE_NAME]
    assert refresh["httponly"]
    # Refresh is path-scoped to the fan surface (A2 broadened it from /refresh so
    # logout can read it) + SameSite=Strict.
    assert refresh["samesite"].lower() == "strict"
    assert refresh["path"] == "/api/fan"


def test_login_unregistered_number_returns_422(client: Client) -> None:
    # A valid OTP but no account → the caller (who controls the phone) is guided to
    # signup. Nobody without the code can distinguish this from a bad code.
    resp = _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code()})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "가입이 필요해요."


def test_login_bad_otp_returns_422_and_does_not_leak_existence(client: Client) -> None:
    _register()
    resp = _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _wrong_code()})
    assert resp.status_code == 422
    # A wrong code and an unregistered number are indistinguishable to a caller
    # who does not hold the code.
    assert resp.json()["detail"] != "가입이 필요해요."


# --- logout ------------------------------------------------------------------


def test_logout_revokes_family_then_me_is_401(client: Client) -> None:
    _register()
    login = _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code()})
    headers = _bearer(login.json()["access_token"])

    assert client.get("/api/fan/me", headers=headers).status_code == 200

    out = client.post("/api/fan/logout", headers=headers)
    assert out.status_code == 200
    assert out.json() == {"status": "ok"}

    # The presented access token's family was revoked → the token is now dead.
    assert client.get("/api/fan/me", headers=headers).status_code == 401


def test_web_logout_clears_auth_cookies(client: Client) -> None:
    _register()
    _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code(), "web": True})
    assert client.get("/api/fan/me").status_code == 200  # cookie surface

    resp = client.post("/api/fan/logout")
    assert resp.status_code == 200
    assert resp.cookies[ACCESS_COOKIE_NAME].value == ""
    assert resp.cookies[REFRESH_COOKIE_NAME].value == ""


def test_web_logout_burns_family_via_refresh_cookie_when_access_expired(
    client: Client,
) -> None:
    """Best-effort logout still burns the family via the refresh cookie alone (A2).

    Simulates an access-expired web session (only the refresh cookie survives): the
    unauthenticated logout must read the refresh cookie and revoke its family (F11).
    """
    _register()
    _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code(), "web": True})
    refresh_plain = client.cookies[REFRESH_COOKIE_NAME].value
    family = RefreshToken.objects.get(token_hash=hash_token(refresh_plain)).family
    assert family.revoked is False

    # Drop the access cookie: the browser now holds only the live refresh cookie.
    del client.cookies[ACCESS_COOKIE_NAME]

    resp = client.post("/api/fan/logout")
    assert resp.status_code == 200

    family.refresh_from_db()
    assert family.revoked is True
    # The refresh lineage is dead: rotating the (still-known) refresh token fails.
    reuse = _post(client, "/api/fan/refresh", {"refresh_token": refresh_plain})
    assert reuse.status_code == 401


# --- refresh -----------------------------------------------------------------


def test_refresh_rotates_on_body_surface(client: Client) -> None:
    _register()
    login = _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code()})
    r1 = login.json()["refresh_token"]

    resp = _post(client, "/api/fan/refresh", {"refresh_token": r1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_delivery"] == "body"
    assert body["access_token"] and body["refresh_token"]
    assert body["refresh_token"] != r1  # the token rotated


def test_refresh_reuse_revokes_the_family(client: Client) -> None:
    _register()
    login = _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code()})
    r1 = login.json()["refresh_token"]

    ok = _post(client, "/api/fan/refresh", {"refresh_token": r1})
    assert ok.status_code == 200
    r2 = ok.json()["refresh_token"]

    # Replaying the consumed r1 is reuse → 401 and the whole family is burned.
    reuse = _post(client, "/api/fan/refresh", {"refresh_token": r1})
    assert reuse.status_code == 401

    # r2 was minted in the same family, so it is dead too after reuse detection.
    after = _post(client, "/api/fan/refresh", {"refresh_token": r2})
    assert after.status_code == 401


def test_refresh_invalid_token_is_401(client: Client) -> None:
    resp = _post(client, "/api/fan/refresh", {"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


def test_refresh_on_cookie_surface_resets_cookies(client: Client) -> None:
    _register()
    _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code(), "web": True})
    old_access = client.cookies[ACCESS_COOKIE_NAME].value

    resp = _post(client, "/api/fan/refresh", {})
    assert resp.status_code == 200
    assert resp.json()["token_delivery"] == "cookie"
    new_access = resp.cookies[ACCESS_COOKIE_NAME].value
    assert new_access and new_access != old_access


def test_refresh_cookie_surface_without_csrf_is_403() -> None:
    """A cookie-surface refresh without the CSRF double-submit token is 403 (A3).

    Uses a CSRF-enforcing client (the default test client short-circuits CSRF), logs
    in on the web surface to plant the refresh cookie, then POSTs to /refresh with no
    ``X-CSRFToken`` — the manual CSRF gate on the cookie surface must reject it.
    """
    csrf_client = Client(enforce_csrf_checks=True)
    _register()
    _post(
        csrf_client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code(), "web": True}
    )
    # Refresh cookie is present, but no CSRF token accompanies the unsafe POST.
    resp = _post(csrf_client, "/api/fan/refresh", {})
    assert resp.status_code == 403


# --- me ----------------------------------------------------------------------


def test_me_requires_auth(client: Client) -> None:
    assert client.get("/api/fan/me").status_code in {401, 403}


def test_me_returns_identity_summary(client: Client) -> None:
    account = _register()
    login = _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code()})
    me = client.get("/api/fan/me", headers=_bearer(login.json()["access_token"]))
    assert me.status_code == 200
    assert me.json() == {
        "id": str(account.fan_id),
        "nickname": "미오팬",
        "role": Role.FAN.value,
        "handle": None,
        "avatar_url": None,
    }


def test_me_includes_creator_handle_and_avatar(client: Client) -> None:
    account = _register()
    Creator.objects.create(
        handle="mio", name="Mio", avatar_url="https://cdn.example/mio.png", owner=account
    )
    login = _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code()})
    body = client.get(
        "/api/fan/me", headers=_bearer(login.json()["access_token"])
    ).json()
    assert body["handle"] == "mio"
    assert body["avatar_url"] == "https://cdn.example/mio.png"


# --- csrf --------------------------------------------------------------------


def test_csrf_endpoint_issues_cookie(client: Client) -> None:
    resp = client.get("/api/fan/csrf")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert "csrftoken" in resp.cookies


# --- resolve_optional_account helper -----------------------------------------


def test_resolve_optional_account_anonymous_is_none() -> None:
    request = RequestFactory().get("/")
    assert resolve_optional_account(request) is None


def test_resolve_optional_account_reads_bearer_header() -> None:
    account = _register()
    pair = issue_token_pair(account)
    request = RequestFactory().get(
        "/", HTTP_AUTHORIZATION=f"Bearer {pair.access_token}"
    )
    resolved = resolve_optional_account(request)
    assert resolved is not None
    assert resolved.pk == account.pk


def test_resolve_optional_account_reads_access_cookie() -> None:
    account = _register()
    pair = issue_token_pair(account)
    request = RequestFactory().get(
        "/", HTTP_COOKIE=f"{ACCESS_COOKIE_NAME}={pair.access_token}"
    )
    resolved = resolve_optional_account(request)
    assert resolved is not None
    assert resolved.pk == account.pk


def test_resolve_optional_account_bad_token_is_none() -> None:
    request = RequestFactory().get("/", HTTP_AUTHORIZATION="Bearer not-a-real-token")
    assert resolve_optional_account(request) is None


# --- anon throttle (A4) ------------------------------------------------------


def _served_operation(view_name: str) -> Any:
    """Find the *bound* (live) Ninja operation whose view function is ``view_name``.

    The operation that actually serves requests is a clone inside the API's bound
    routers (Ninja clones templates at URL-generation time), so injecting a throttle
    onto the module-level router object would not affect serving. This walks the
    bound routers to reach the real operation.
    """
    for bound in api._get_bound_routers():
        for path_view in bound.path_operations.values():
            for operation in path_view.operations:
                if getattr(operation.view_func, "__name__", "") == view_name:
                    return operation
    raise LookupError(f"served operation not found: {view_name}")


def test_signup_otp_is_ip_throttled(client: Client) -> None:
    """The signup-OTP endpoint returns 429 once the per-IP rate is exceeded (A4).

    Works around the decoration-time throttle gate (see ``config.throttle`` TRAP
    note): the test suite freezes ``FAN_WRITE_THROTTLE_ENABLED=False`` at import, so
    ``override_settings`` cannot re-enable it. Instead we inject an
    :class:`AnonRateThrottle` directly onto the live served operation, exercise the
    real endpoint until the bucket is full, and restore it afterwards.
    """
    operation = _served_operation("request_otp")
    original = list(operation.throttle_objects)
    operation.throttle_objects = [AnonRateThrottle("5/min")]
    cache.clear()
    body: dict[str, object] = {"phone": _PHONE}
    try:
        # Five requests fit the 5/min bucket…
        for _ in range(5):
            ok = _post(client, "/api/fan/signup/otp", body)
            assert ok.status_code == 200
        # …the sixth from the same IP is throttled.
        blocked = _post(client, "/api/fan/signup/otp", body)
        assert blocked.status_code == 429
    finally:
        operation.throttle_objects = original
        cache.clear()
