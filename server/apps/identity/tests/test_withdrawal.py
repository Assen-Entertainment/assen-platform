"""Tests for fan account withdrawal (D3, privacy decisions 2026-07-12).

Withdrawal anonymises the account in place (clears nickname + phone hash, sets
is_active False, stamps withdrawn_at) and revokes every session, while keeping the
row so legal-hold records stay linked to a pseudonymous fan_id.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client

from apps.identity.models import Account, TokenFamily
from apps.identity.services import issue_token_pair, withdraw_account
from apps.identity.signup_services import hash_phone, register_fan
from config.otp import MockOtpSender

pytestmark = pytest.mark.django_db

_SENDER = MockOtpSender()
_PHONE = "+821012345678"


def _register(phone: str = _PHONE, nickname: str = "미오팬") -> Account:
    register_fan(
        phone=phone,
        nickname=nickname,
        consent_terms=True,
        consent_privacy=True,
        otp_code=_SENDER.code_for(phone),
        otp_sender=_SENDER,
    )
    return Account.objects.get(auth_subject_hash=hash_phone(phone))


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
    # Login filters is_active=True, so a withdrawn account looks unregistered.
    resp = _post(
        client, "/api/fan/login", {"phone": _PHONE, "otp_code": _SENDER.code_for(_PHONE)}
    )
    assert resp.status_code == 422


def test_resignup_after_withdrawal_creates_a_fresh_account(client: Client) -> None:
    account = _register()
    old_fan_id = account.fan_id
    withdraw_account(account)

    resp = _post(
        client,
        "/api/fan/signup",
        {
            "phone": _PHONE,
            "otp_code": _SENDER.code_for(_PHONE),
            "nickname": "새미오",
            "consent_terms": True,
            "consent_privacy": True,
            "age_over_14": True,
        },
    )
    assert resp.status_code == 200

    # A brand-new active account holds the phone; the withdrawn one stays anonymised.
    fresh = Account.objects.get(auth_subject_hash=hash_phone(_PHONE))
    assert fresh.fan_id != old_fan_id
    assert fresh.is_active is True
    assert fresh.nickname == "새미오"
    old = Account.objects.get(fan_id=old_fan_id)
    assert old.is_active is False
    assert old.auth_subject_hash == ""


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
