"""ASS-287 A-2 — the phone identifier is a keyed HMAC (``v1:``), and pre-A-2
accounts keyed by the bare SHA-256 are migrated in place on access (dual-read).
"""

from __future__ import annotations

import hashlib
import json

import pytest
from django.test import Client

from apps.identity.models import Account, Role
from apps.identity.signup_services import hash_phone, migrate_legacy_subject_hash
from config.otp import MockOtpSender

pytestmark = pytest.mark.django_db

_SENDER = MockOtpSender()
_PHONE = "+821012345678"  # already normalize_phone()d


def _legacy(phone: str) -> str:
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


def test_hash_is_versioned_hmac_without_the_phone() -> None:
    h = hash_phone(_PHONE)
    assert h.startswith("v1:")
    assert "1012345678" not in h  # the number is not embedded
    assert h != _legacy(_PHONE)  # not the brute-forceable bare digest
    assert len(h) <= 64  # fits the existing auth_subject_hash column


def test_migrate_rekeys_a_legacy_account_in_place() -> None:
    acc = Account.objects.create(
        auth_subject_hash=_legacy(_PHONE),
        role=Role.FAN.value,
        is_active=True,
        nickname="구팬",
        auth_method="phone",
    )
    migrate_legacy_subject_hash(_PHONE)
    acc.refresh_from_db()
    assert acc.auth_subject_hash == hash_phone(_PHONE)
    assert Account.objects.count() == 1  # rekeyed in place, not duplicated


def test_migrate_is_noop_for_a_v1_account() -> None:
    acc = Account.objects.create(
        auth_subject_hash=hash_phone(_PHONE),
        role=Role.FAN.value,
        is_active=True,
        nickname="새팬",
        auth_method="phone",
    )
    migrate_legacy_subject_hash(_PHONE)
    acc.refresh_from_db()
    assert acc.auth_subject_hash == hash_phone(_PHONE)
    assert Account.objects.count() == 1


def test_login_migrates_a_legacy_account_and_does_not_duplicate(client: Client) -> None:
    acc = Account.objects.create(
        auth_subject_hash=_legacy(_PHONE),
        role=Role.FAN.value,
        is_active=True,
        nickname="구팬",
        auth_method="phone",
    )
    resp = client.post(
        "/api/fan/login",
        data=json.dumps({"phone": _PHONE, "otp_code": _SENDER.code_for(_PHONE)}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    acc.refresh_from_db()
    assert acc.auth_subject_hash == hash_phone(_PHONE)
    assert acc.auth_subject_hash.startswith("v1:")
    assert Account.objects.filter(role=Role.FAN.value).count() == 1
