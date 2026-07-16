"""Tests for the fan re-auth / session endpoints (ASS-237).

Covers logout revocation + cookie clearing, refresh rotation + reuse detection, the
``/me`` contract, the ``/csrf`` cookie, and the ``resolve_optional_account`` helper.
Phone-OTP login was retired (auth redesign), so sessions are established directly
(``issue_token_pair``) or, where a cookie surface is needed, via the retained email
login endpoint. The phone-vs-email login behaviour itself lives in ``test_email_auth``.

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client, RequestFactory
from django.utils import timezone

from apps.creator.models import Creator
from apps.identity.auth import resolve_optional_account
from apps.identity.cookies import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from apps.identity.models import Account, RefreshToken, Role
from apps.identity.services import hash_token, issue_token_pair

pytestmark = pytest.mark.django_db

_EMAIL = "fan@example.com"
_PASSWORD = "correct horse 8"


def _register(nickname: str = "미오팬") -> Account:
    """Create a verified email fan directly (phone login was retired)."""
    return Account.objects.create(
        role=Role.FAN.value,
        email=_EMAIL,
        password_hash=make_password(_PASSWORD),
        email_verified_at=timezone.now(),
        nickname=nickname,
        auth_method="email",
    )


def _post(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.post(
        path, data=json.dumps(body), content_type="application/json", **extra
    )


def _login_web(client: Client) -> Any:
    """Log in on the web (cookie) surface via the retained email endpoint."""
    return _post(
        client,
        "/api/fan/login/email",
        {"email": _EMAIL, "password": _PASSWORD, "web": True},
    )


def _bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


# --- logout ------------------------------------------------------------------


def test_logout_revokes_family_then_me_is_401(client: Client) -> None:
    account = _register()
    headers = _bearer(issue_token_pair(account).access_token)

    assert client.get("/api/fan/me", headers=headers).status_code == 200

    out = client.post("/api/fan/logout", headers=headers)
    assert out.status_code == 200
    assert out.json() == {"status": "ok"}

    # The presented access token's family was revoked → the token is now dead.
    assert client.get("/api/fan/me", headers=headers).status_code == 401


def test_web_logout_clears_auth_cookies(client: Client) -> None:
    _register()
    _login_web(client)
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
    _login_web(client)
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
    account = _register()
    r1 = issue_token_pair(account).refresh_token

    resp = _post(client, "/api/fan/refresh", {"refresh_token": r1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_delivery"] == "body"
    assert body["access_token"] and body["refresh_token"]
    assert body["refresh_token"] != r1  # the token rotated


def test_refresh_reuse_revokes_the_family(client: Client) -> None:
    account = _register()
    r1 = issue_token_pair(account).refresh_token

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
    _login_web(client)
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
    _login_web(csrf_client)
    # Refresh cookie is present, but no CSRF token accompanies the unsafe POST.
    resp = _post(csrf_client, "/api/fan/refresh", {})
    assert resp.status_code == 403


# --- me ----------------------------------------------------------------------


def test_me_requires_auth(client: Client) -> None:
    assert client.get("/api/fan/me").status_code in {401, 403}


def test_me_returns_identity_summary(client: Client) -> None:
    account = _register()
    token = issue_token_pair(account).access_token
    me = client.get("/api/fan/me", headers=_bearer(token))
    assert me.status_code == 200
    assert me.json() == {
        "id": str(account.fan_id),
        "nickname": "미오팬",
        "role": Role.FAN.value,
        "handle": None,
        "avatar_url": None,
        # R3: derived 인증 flags added to the session bootstrap (fail-closed default).
        "adult_verified": False,
        "kyc_status": "unverified",
    }


def test_me_includes_creator_handle_and_avatar(client: Client) -> None:
    account = _register()
    Creator.objects.create(
        handle="mio", name="Mio", avatar_url="https://cdn.example/mio.png", owner=account
    )
    token = issue_token_pair(account).access_token
    body = client.get("/api/fan/me", headers=_bearer(token)).json()
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
