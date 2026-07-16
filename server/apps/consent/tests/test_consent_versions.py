"""Consent-document version plumbing (#20-versioning).

Consent capture must record WHICH policy text a fan agreed to. These tests prove the
server consent version registry (:mod:`apps.consent.versions`) is stamped onto the
terms/privacy ConsentRecords at phone signup and first-time social registration, and
that the anonymous ``/api/fan/consent/versions`` endpoint advertises the same
registry so the signup page can present + echo the presented versions.

법무-게이트: the version VALUES are placeholders; these tests assert the *plumbing*
(the recorded version equals the registry), not any specific legal string.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.consent.models import ConsentKind, ConsentRecord
from apps.consent.versions import CONSENT_DOC_VERSIONS, consent_doc_version
from apps.identity.models import Account, Role
from apps.identity.signup_services import hash_phone, register_fan
from apps.identity.social_services import hash_social, register_or_login_social
from config.otp import MockOtpSender

_SENDER = MockOtpSender()
_PHONE = "+821012345678"


def _recorded_version(account: Account, kind: str) -> str:
    return ConsentRecord.objects.get(account=account, kind=kind).version


# --- registry accessor -------------------------------------------------------


def test_registry_covers_signup_documents() -> None:
    # The three presented consent documents are versioned in the registry.
    assert set(CONSENT_DOC_VERSIONS) == {
        ConsentKind.TERMS.value,
        ConsentKind.PRIVACY.value,
        ConsentKind.AGE.value,
    }
    for kind, version in CONSENT_DOC_VERSIONS.items():
        assert consent_doc_version(kind) == version
        assert version  # a non-empty placeholder is present


def test_registry_accessor_is_keyerror_safe() -> None:
    # Unversioned/unknown kinds (rule/marketing carry their own per-grant strings)
    # return "" so the value can go straight into record_consent without a guard.
    assert consent_doc_version(ConsentKind.RULE.value) == ""
    assert consent_doc_version("does-not-exist") == ""


# --- phone signup ------------------------------------------------------------


@pytest.mark.django_db
def test_phone_signup_records_registry_versions() -> None:
    register_fan(
        phone=_PHONE,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_SENDER.code_for(_PHONE),
        otp_sender=_SENDER,
    )
    account = Account.objects.get(auth_subject_hash=hash_phone(_PHONE))

    assert _recorded_version(account, ConsentKind.TERMS.value) == (
        CONSENT_DOC_VERSIONS[ConsentKind.TERMS.value]
    )
    assert _recorded_version(account, ConsentKind.PRIVACY.value) == (
        CONSENT_DOC_VERSIONS[ConsentKind.PRIVACY.value]
    )


@pytest.mark.django_db
def test_phone_signup_version_override_still_pins_both() -> None:
    # An explicit version override keeps the back-compat pin for both documents.
    register_fan(
        phone=_PHONE,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_SENDER.code_for(_PHONE),
        otp_sender=_SENDER,
        version="pinned-1",
    )
    account = Account.objects.get(auth_subject_hash=hash_phone(_PHONE))
    assert _recorded_version(account, ConsentKind.TERMS.value) == "pinned-1"
    assert _recorded_version(account, ConsentKind.PRIVACY.value) == "pinned-1"


# --- social first registration ----------------------------------------------


@pytest.mark.django_db
def test_first_social_registration_records_registry_versions() -> None:
    register_or_login_social(
        provider="kakao",
        subject="u1",
        display_name="카카오유저",
        consent_terms=True,
        consent_privacy=True,
        age_over_14=True,
    )
    account = Account.objects.get(auth_subject_hash=hash_social("kakao", "u1"))
    assert account.role == Role.FAN.value

    assert _recorded_version(account, ConsentKind.TERMS.value) == (
        CONSENT_DOC_VERSIONS[ConsentKind.TERMS.value]
    )
    assert _recorded_version(account, ConsentKind.PRIVACY.value) == (
        CONSENT_DOC_VERSIONS[ConsentKind.PRIVACY.value]
    )


# --- endpoint ----------------------------------------------------------------


@pytest.mark.django_db
def test_versions_endpoint_returns_registry_anonymously(client: Client) -> None:
    # No auth header: the signup page is anonymous and must reach this.
    resp = client.get("/api/fan/consent/versions")
    assert resp.status_code == 200
    assert resp.json() == {
        "terms": CONSENT_DOC_VERSIONS[ConsentKind.TERMS.value],
        "privacy": CONSENT_DOC_VERSIONS[ConsentKind.PRIVACY.value],
        "age": CONSENT_DOC_VERSIONS[ConsentKind.AGE.value],
    }
