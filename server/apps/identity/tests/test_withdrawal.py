"""Tests for fan account withdrawal (D3, privacy decisions 2026-07-12).

Withdrawal anonymises the account in place (clears nickname + phone hash + email, sets
is_active False, stamps withdrawn_at) and revokes every session, while keeping the row
so legal-hold records stay linked to a pseudonymous fan_id. Phone-OTP signup/login was
retired (auth redesign), so accounts are created directly and the login/re-signup
behaviour is exercised through the retained email endpoints.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone

from apps.identity.models import Account, Role, TokenFamily
from apps.identity.services import issue_token_pair, withdraw_account

pytestmark = pytest.mark.django_db

_EMAIL = "fan@example.com"
_PASSWORD = "correct horse 8"


def _register(nickname: str = "미오팬") -> Account:
    """Create a verified email fan directly (phone signup was retired)."""
    return Account.objects.create(
        role=Role.FAN.value,
        email=_EMAIL,
        password_hash=make_password(_PASSWORD),
        email_verified_at=timezone.now(),
        nickname=nickname,
        auth_method="email",
    )


def _bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def _post(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.post(
        path, data=json.dumps(body), content_type="application/json", **extra
    )


def test_withdraw_anonymizes_and_revokes_sessions() -> None:
    account = _register()
    issue_token_pair(account)  # a live session that must be cut off
    withdraw_account(account)

    account.refresh_from_db()
    assert account.nickname == ""
    assert account.auth_subject_hash == ""
    assert account.is_active is False
    assert account.withdrawn_at is not None
    # No PII survives beyond the anonymised row; every token family is revoked.
    assert not TokenFamily.objects.filter(account=account, revoked=False).exists()


def test_withdraw_is_idempotent() -> None:
    account = _register()
    withdraw_account(account)
    account.refresh_from_db()
    first_ts = account.withdrawn_at

    withdraw_account(account)  # already withdrawn → no-op, timestamp unchanged
    account.refresh_from_db()
    assert account.withdrawn_at == first_ts


def test_withdrawn_account_cannot_login(client: Client) -> None:
    account = _register()
    withdraw_account(account)
    # login_email filters is_active=True (and withdrawal clears the email), so a
    # withdrawn account is indistinguishable from an unknown one (422).
    resp = _post(
        client, "/api/fan/login/email", {"email": _EMAIL, "password": _PASSWORD}
    )
    assert resp.status_code == 422


def test_resignup_after_withdrawal_creates_a_fresh_account(client: Client) -> None:
    account = _register()
    old_fan_id = account.fan_id
    withdraw_account(account)

    # The freed email backs a brand-new signup (uniq_fan_email is partial on non-empty,
    # and withdrawal emptied it), which verifies into a fresh active account.
    signup = _post(
        client,
        "/api/fan/signup/email",
        {
            "email": _EMAIL,
            "password": _PASSWORD,
            "nickname": "새미오",
            "consent_terms": True,
            "consent_privacy": True,
            "age_over_14": True,
        },
    )
    assert signup.status_code == 200
    verify = _post(
        client, "/api/fan/verify-email", {"token": signup.json()["verification_token"]}
    )
    assert verify.status_code == 200

    # A brand-new active account holds the email; the withdrawn one stays anonymised.
    fresh = Account.objects.get(email=_EMAIL, is_active=True)
    assert fresh.fan_id != old_fan_id
    assert fresh.is_active is True
    assert fresh.nickname == "새미오"
    old = Account.objects.get(fan_id=old_fan_id)
    assert old.is_active is False
    assert old.email == ""


def test_withdraw_endpoint_requires_auth(client: Client) -> None:
    resp = client.post("/api/fan/account/withdraw")
    assert resp.status_code in (401, 403)


def test_withdraw_endpoint_ends_session(client: Client) -> None:
    account = _register()
    pair = issue_token_pair(account)
    resp = client.post(
        "/api/fan/account/withdraw", headers=_bearer(pair.access_token)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "withdrawn"
    account.refresh_from_db()
    assert account.is_active is False
    assert account.withdrawn_at is not None
