"""Tests for the optional marketing-consent capture at fan signup (Codex #20).

The phone-signup form offers a "마케팅 수신(선택)" checkbox. When ticked, signup must
record an SMS marketing opt-in (the only channel reachable at signup is the phone →
SMS); push/email stay default-off until the user sets them in /settings/notifications.
When left unticked (or omitted), signup must record NO marketing opt-in (fail-closed).
"""

from __future__ import annotations

import json

import pytest
from django.test import Client

from apps.consent.models import ConsentKind, ConsentRecord, MarketingConsent
from apps.consent.services import marketing_consent_state
from apps.identity.models import Account, Role
from apps.identity.signup_services import hash_phone, register_fan
from config.otp import MockOtpSender

pytestmark = pytest.mark.django_db

_SENDER = MockOtpSender()
_PHONE = "+821012345678"


def _code(phone: str = _PHONE) -> str:
    return _SENDER.code_for(phone)


def _account() -> Account:
    return Account.objects.get(auth_subject_hash=hash_phone(_PHONE))


def _signup(client: Client, **overrides: object) -> int:
    body: dict[str, object] = {
        "phone": _PHONE,
        "otp_code": _code(),
        "nickname": "미오팬",
        "consent_terms": True,
        "consent_privacy": True,
        "age_over_14": True,
    }
    body.update(overrides)
    response = client.post(
        "/api/fan/signup", data=json.dumps(body), content_type="application/json"
    )
    return response.status_code


# --- service: register_fan ---------------------------------------------------


def test_register_fan_records_sms_optin_when_marketing_true() -> None:
    register_fan(
        phone=_PHONE,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        marketing_consent=True,
        otp_code=_code(),
        otp_sender=_SENDER,
    )
    account = _account()
    # Only SMS is opted in — push/email stay default-off (fail-closed) at signup.
    assert marketing_consent_state(account) == {
        "push": False,
        "sms": True,
        "email": False,
    }
    assert MarketingConsent.objects.filter(
        account=account, channel="sms", enabled=True
    ).exists()
    # The opt-in also appends a durable marketing ConsentRecord audit row.
    assert ConsentRecord.objects.filter(
        account=account, kind=ConsentKind.MARKETING.value
    ).exists()


def test_register_fan_records_no_optin_when_marketing_false() -> None:
    register_fan(
        phone=_PHONE,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        marketing_consent=False,
        otp_code=_code(),
        otp_sender=_SENDER,
    )
    account = _account()
    assert marketing_consent_state(account) == {
        "push": False,
        "sms": False,
        "email": False,
    }
    assert not MarketingConsent.objects.filter(account=account).exists()
    assert not ConsentRecord.objects.filter(
        account=account, kind=ConsentKind.MARKETING.value
    ).exists()


def test_register_fan_records_no_optin_when_marketing_omitted() -> None:
    # The param is optional (default False): existing callers that never pass it
    # must record no marketing opt-in.
    register_fan(
        phone=_PHONE,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_code(),
        otp_sender=_SENDER,
    )
    account = _account()
    assert marketing_consent_state(account)["sms"] is False
    assert not MarketingConsent.objects.filter(account=account).exists()


# --- API: /fan/signup --------------------------------------------------------


def test_signup_endpoint_records_sms_optin_when_marketing_true(client: Client) -> None:
    assert _signup(client, marketing_consent=True) == 200
    account = Account.objects.get(role=Role.FAN.value)
    assert marketing_consent_state(account)["sms"] is True


def test_signup_endpoint_records_no_optin_when_marketing_false(client: Client) -> None:
    assert _signup(client, marketing_consent=False) == 200
    account = Account.objects.get(role=Role.FAN.value)
    assert marketing_consent_state(account)["sms"] is False
    assert not MarketingConsent.objects.filter(account=account).exists()


def test_signup_endpoint_records_no_optin_when_marketing_omitted(
    client: Client,
) -> None:
    # marketing_consent has a fail-closed default (False), so omitting it entirely
    # records no opt-in — the field is genuinely optional on the wire.
    assert _signup(client) == 200
    account = Account.objects.get(role=Role.FAN.value)
    assert marketing_consent_state(account)["sms"] is False
    assert not MarketingConsent.objects.filter(account=account).exists()
