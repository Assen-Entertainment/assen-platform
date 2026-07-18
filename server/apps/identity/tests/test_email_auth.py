"""Tests for email + password fan auth (additive to phone OTP / social).

Covers the full flow — signup creates an *unverified* account (no token pair), login
is refused until verify, the emailed token verifies + logs in, and post-verify login
issues tokens — plus the disclosure-safe login (wrong password == unknown email), the
duplicate-verified-email refusal, and the fail-closed 503 when the mock email sender is
off. The verification token is read straight off the signup response
(``EMAIL_VERIFY_RETURN_TOKEN`` is on in the test settings).

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client, override_settings

from apps.identity.cookies import ACCESS_COOKIE_NAME
from apps.identity.models import Account, Role

pytestmark = pytest.mark.django_db

_EMAIL = "fan@example.com"
_PASSWORD = "correct horse 8"
_NICKNAME = "이메일팬"


def _post(client: Client, path: str, body: dict[str, object]) -> Any:
    return client.post(
        path, data=json.dumps(body), content_type="application/json"
    )


def _signup(
    client: Client,
    *,
    email: str = _EMAIL,
    password: str = _PASSWORD,
    nickname: str = _NICKNAME,
) -> Any:
    return _post(
        client,
        "/api/fan/signup/email",
        {
            "email": email,
            "password": password,
            "nickname": nickname,
            "consent_terms": True,
            "consent_privacy": True,
            "age_over_14": True,
        },
    )


def _verify(client: Client, token: str) -> Any:
    return _post(client, "/api/fan/verify-email", {"token": token})


def _register_verified(client: Client, *, email: str = _EMAIL) -> None:
    """Sign up and confirm the emailed token so the account can log in."""
    resp = _signup(client, email=email)
    _verify(client, resp.json()["verification_token"])


# --- signup ------------------------------------------------------------------


def test_signup_creates_unverified_account_without_tokens(client: Client) -> None:
    resp = _signup(client)
    assert resp.status_code == 200
    body: dict[str, Any] = resp.json()
    assert body["status"] == "verification_sent"
    assert body["verification_token"]  # dev flag echoes it for QA
    # No auth token is delivered at signup (login happens on verify).
    assert ACCESS_COOKIE_NAME not in resp.cookies
    account = Account.objects.get(email=_EMAIL, role=Role.FAN.value)
    assert account.email_verified_at is None
    assert account.password_hash  # password stored (hashed), never the plaintext
    assert account.password_hash != _PASSWORD


def test_login_before_verify_is_403_email_not_verified(client: Client) -> None:
    _signup(client)
    resp = _post(
        client, "/api/fan/login/email", {"email": _EMAIL, "password": _PASSWORD}
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "EmailNotVerified"


# --- verify ------------------------------------------------------------------


def test_verify_email_marks_verified_and_issues_tokens(client: Client) -> None:
    signup = _signup(client)
    token = signup.json()["verification_token"]
    resp = _verify(client, token)
    assert resp.status_code == 200
    body: dict[str, Any] = resp.json()
    assert body["token_delivery"] == "body"
    assert body["access_token"] and body["refresh_token"]
    account = Account.objects.get(email=_EMAIL)
    assert account.email_verified_at is not None


def test_verify_email_web_surface_sets_cookies(client: Client) -> None:
    signup = _signup(client)
    token = signup.json()["verification_token"]
    resp = _post(client, "/api/fan/verify-email", {"token": token, "web": True})
    assert resp.status_code == 200
    assert resp.json()["token_delivery"] == "cookie"
    assert ACCESS_COOKIE_NAME in resp.cookies


def test_verify_bad_token_is_400(client: Client) -> None:
    resp = _verify(client, "not-a-real-token")
    assert resp.status_code == 400
    assert resp.json()["code"] == "EmailVerificationInvalid"


# --- login -------------------------------------------------------------------


def test_login_after_verify_issues_tokens(client: Client) -> None:
    _register_verified(client)
    resp = _post(
        client, "/api/fan/login/email", {"email": _EMAIL, "password": _PASSWORD}
    )
    assert resp.status_code == 200
    body: dict[str, Any] = resp.json()
    assert body["access_token"] and body["refresh_token"]


def test_login_is_case_insensitive_on_email(client: Client) -> None:
    _register_verified(client)
    resp = _post(
        client,
        "/api/fan/login/email",
        {"email": _EMAIL.upper(), "password": _PASSWORD},
    )
    assert resp.status_code == 200


def test_wrong_password_indistinguishable_from_unknown_email(client: Client) -> None:
    _register_verified(client)
    wrong_pw = _post(
        client, "/api/fan/login/email", {"email": _EMAIL, "password": "wrong pw 8x"}
    )
    unknown = _post(
        client,
        "/api/fan/login/email",
        {"email": "nobody@example.com", "password": _PASSWORD},
    )
    assert wrong_pw.status_code == unknown.status_code == 422
    # A wrong password and an unknown email are byte-identical to the caller.
    assert wrong_pw.json() == unknown.json()
    assert wrong_pw.json()["code"] == "InvalidCredentials"


# --- duplicate + availability ------------------------------------------------


def test_duplicate_verified_email_is_409(client: Client) -> None:
    _register_verified(client)
    resp = _signup(client)  # same email, now verified
    assert resp.status_code == 409
    assert resp.json()["code"] == "EmailAlreadyRegistered"


@override_settings(ENABLE_MOCK_EMAIL=False)
def test_signup_unavailable_when_email_mock_off(client: Client) -> None:
    # Fail-closed: with no email sender wired, signup must refuse and create nothing.
    resp = _signup(client)
    assert resp.status_code == 503
    assert resp.json()["code"] == "EmailUnavailable"
    assert not Account.objects.filter(email=_EMAIL).exists()
