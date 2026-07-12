"""Tests for per-channel marketing consent (D8, privacy decisions 2026-07-12).

Marketing consent is optional and per-channel: a current-state MarketingConsent row
per (account, channel) drives the send-time gate, and each change appends a durable
ConsentRecord audit row. Withdrawal clears every channel.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client

from apps.consent.models import ConsentKind, ConsentRecord, MarketingConsent
from apps.consent.services import (
    clear_marketing_consent,
    marketing_consent_state,
    set_marketing_consent,
)
from apps.identity.models import Account
from apps.identity.services import issue_token_pair, withdraw_account
from apps.identity.signup_services import hash_phone, register_fan
from config.otp import MockOtpSender

pytestmark = pytest.mark.django_db

_SENDER = MockOtpSender()
_PHONE = "+821012345678"


def _register(phone: str = _PHONE) -> Account:
    register_fan(
        phone=phone,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_SENDER.code_for(phone),
        otp_sender=_SENDER,
    )
    return Account.objects.get(auth_subject_hash=hash_phone(phone))


def _bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def test_default_state_is_all_off() -> None:
    account = _register()
    assert marketing_consent_state(account) == {
        "push": False,
        "sms": False,
        "email": False,
    }


def test_set_channel_updates_state_and_writes_audit() -> None:
    account = _register()
    set_marketing_consent(account=account, channel="push", enabled=True)

    assert marketing_consent_state(account)["push"] is True
    # A durable audit row is appended for the grant.
    assert ConsentRecord.objects.filter(
        account=account,
        kind=ConsentKind.MARKETING.value,
        version="marketing:push:on",
    ).exists()


def test_toggling_a_channel_upserts_one_row() -> None:
    account = _register()
    set_marketing_consent(account=account, channel="sms", enabled=True)
    set_marketing_consent(account=account, channel="sms", enabled=False)

    rows = MarketingConsent.objects.filter(account=account, channel="sms")
    assert rows.count() == 1
    assert MarketingConsent.objects.get(account=account, channel="sms").enabled is False
    assert marketing_consent_state(account)["sms"] is False


def test_unknown_channel_is_rejected() -> None:
    account = _register()
    with pytest.raises(ValueError):
        set_marketing_consent(account=account, channel="carrier_pigeon", enabled=True)


def test_clear_disables_every_channel() -> None:
    account = _register()
    set_marketing_consent(account=account, channel="push", enabled=True)
    set_marketing_consent(account=account, channel="sms", enabled=True)

    clear_marketing_consent(account)
    assert marketing_consent_state(account) == {
        "push": False,
        "sms": False,
        "email": False,
    }


def test_withdrawal_clears_marketing_consent() -> None:
    account = _register()
    set_marketing_consent(account=account, channel="push", enabled=True)

    withdraw_account(account)
    assert marketing_consent_state(account)["push"] is False


# --- endpoints ---------------------------------------------------------------


def test_get_marketing_requires_auth(client: Client) -> None:
    assert client.get("/api/fan/marketing").status_code in (401, 403)


def test_get_and_put_marketing_roundtrip(client: Client) -> None:
    account = _register()
    headers = _bearer(issue_token_pair(account).access_token)

    initial = client.get("/api/fan/marketing", headers=headers)
    assert initial.status_code == 200
    assert initial.json() == {"push": False, "sms": False, "email": False}

    saved = client.put(
        "/api/fan/marketing",
        data=json.dumps({"push": True, "sms": False, "email": False}),
        content_type="application/json",
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json() == {"push": True, "sms": False, "email": False}
    # And it persists on the next read.
    assert client.get("/api/fan/marketing", headers=headers).json()["push"] is True
