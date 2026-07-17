"""Tests for the optional marketing-consent capture at email fan signup.

The email-signup form offers a "마케팅 수신(선택)" checkbox. When ticked, signup must
record an **email** marketing opt-in — the only channel reachable at email signup is the
address the fan just handed over; push/sms stay default-off until the fan sets them in
/settings/notifications. When left unticked (or omitted), signup must record NO
marketing opt-in (fail-closed).

Carries over the "signup records a marketing opt-in" assertion from the deleted
phone-signup coverage (test_signup_marketing_consent.py, dropped with the phone-OTP
surface) onto the email surface — the channel is ``email``, never ``sms``.

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client

from apps.consent.models import ConsentKind, ConsentRecord, MarketingConsent
from apps.consent.services import marketing_consent_state
from apps.identity.email_services import register_fan_email
from apps.identity.models import Account, Role
from config.email import MockEmailSender

pytestmark = pytest.mark.django_db

_EMAIL = "fan@example.com"
_PASSWORD = "correct horse 8"
_NICKNAME = "이메일팬"


def _account() -> Account:
    return Account.objects.get(email=_EMAIL, role=Role.FAN.value)


def _signup(client: Client, **overrides: object) -> Any:
    body: dict[str, object] = {
        "email": _EMAIL,
        "password": _PASSWORD,
        "nickname": _NICKNAME,
        "consent_terms": True,
        "consent_privacy": True,
        "age_over_14": True,
    }
    body.update(overrides)
    return client.post(
        "/api/fan/signup/email",
        data=json.dumps(body),
        content_type="application/json",
    )


# --- service: register_fan_email ---------------------------------------------


def test_register_fan_email_records_email_optin_when_marketing_true() -> None:
    register_fan_email(
        email=_EMAIL,
        password=_PASSWORD,
        nickname=_NICKNAME,
        consent_terms=True,
        consent_privacy=True,
        age_over_14=True,
        marketing_consent=True,
        email_sender=MockEmailSender(),
    )
    account = _account()
    # Only email is opted in — push/sms stay default-off (fail-closed) at signup.
    # sms in particular must NOT be set: the phone surface no longer exists.
    assert marketing_consent_state(account) == {
        "push": False,
        "sms": False,
        "email": True,
    }
    assert MarketingConsent.objects.filter(
        account=account, channel="email", enabled=True
    ).exists()
    # The opt-in also appends a durable marketing ConsentRecord audit row.
    assert ConsentRecord.objects.filter(
        account=account, kind=ConsentKind.MARKETING.value
    ).exists()


def test_register_fan_email_records_no_optin_when_marketing_false() -> None:
    register_fan_email(
        email=_EMAIL,
        password=_PASSWORD,
        nickname=_NICKNAME,
        consent_terms=True,
        consent_privacy=True,
        age_over_14=True,
        marketing_consent=False,
        email_sender=MockEmailSender(),
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


def test_register_fan_email_records_no_optin_when_marketing_omitted() -> None:
    # The param is optional (default False): callers that never pass it must record
    # no marketing opt-in.
    register_fan_email(
        email=_EMAIL,
        password=_PASSWORD,
        nickname=_NICKNAME,
        consent_terms=True,
        consent_privacy=True,
        age_over_14=True,
        email_sender=MockEmailSender(),
    )
    account = _account()
    assert marketing_consent_state(account)["email"] is False
    assert not MarketingConsent.objects.filter(account=account).exists()


# --- API: /fan/signup/email --------------------------------------------------


def test_signup_endpoint_records_email_optin_when_marketing_true(
    client: Client,
) -> None:
    assert _signup(client, marketing_consent=True).status_code == 200
    account = _account()
    assert marketing_consent_state(account)["email"] is True
    # The opt-in is bound to the email channel, not the retired sms one.
    assert marketing_consent_state(account)["sms"] is False
    assert MarketingConsent.objects.filter(
        account=account, channel="email", enabled=True
    ).exists()


def test_signup_endpoint_records_no_optin_when_marketing_false(
    client: Client,
) -> None:
    assert _signup(client, marketing_consent=False).status_code == 200
    account = _account()
    assert marketing_consent_state(account)["email"] is False
    assert not MarketingConsent.objects.filter(account=account).exists()


def test_signup_endpoint_records_no_optin_when_marketing_omitted(
    client: Client,
) -> None:
    # marketing_consent has a fail-closed default (False), so omitting it entirely
    # records no opt-in — the field is genuinely optional on the wire.
    assert _signup(client).status_code == 200
    account = _account()
    assert marketing_consent_state(account)["email"] is False
    assert not MarketingConsent.objects.filter(account=account).exists()
