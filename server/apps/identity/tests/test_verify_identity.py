"""Tests for the fan 본인인증(KYC) + profile-edit surface (R3, gated features).

Covers /fan/verify/start + /fan/verify/confirm (the mock verifier sets the derived
adult flag + kyc_status and records the AGE consent), PATCH /fan/me (nickname), the
extended /fan/me contract, unauth 401s, and the 503 fail-closed when no verifier is
wired (ENABLE_MOCK_KYC off).

HUMAN-REVIEW-REQUIRED: auth/identity (CONSTRAINTS #26).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client, override_settings

from apps.consent.models import ConsentKind, ConsentRecord
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db


def _fan() -> Account:
    return Account.objects.create(role=Role.FAN.value, nickname="미오팬")


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _patch(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.patch(
        path, data=json.dumps(body), content_type="application/json", **extra
    )


# --- verify ------------------------------------------------------------------


def test_verify_start_requires_auth(client: Client) -> None:
    assert client.post("/api/fan/verify/start").status_code in {401, 403}


def test_verify_confirm_requires_auth(client: Client) -> None:
    assert client.post("/api/fan/verify/confirm").status_code in {401, 403}


def test_verify_start_moves_to_pending(client: Client) -> None:
    fan = _fan()
    resp = client.post("/api/fan/verify/start", headers=_auth(fan))
    assert resp.status_code == 200
    fan.refresh_from_db()
    assert fan.kyc_status == KycStatus.PENDING.value
    assert fan.adult_verified is False  # not yet confirmed


def test_verify_confirm_sets_adult_status_and_records_age_consent(
    client: Client,
) -> None:
    fan = _fan()
    resp = client.post("/api/fan/verify/confirm", headers=_auth(fan))
    assert resp.status_code == 200
    body = resp.json()
    assert body["adult_verified"] is True
    assert body["kyc_status"] == KycStatus.VERIFIED.value

    fan.refresh_from_db()
    assert fan.adult_verified is True
    assert fan.kyc_status == KycStatus.VERIFIED.value
    assert fan.kyc_verified_at is not None
    # The AGE consent is recorded so the age-gate has a durable grant.
    assert ConsentRecord.objects.filter(
        account=fan, kind=ConsentKind.AGE.value
    ).exists()


@override_settings(ENABLE_MOCK_KYC=False)
def test_verify_fails_closed_when_no_verifier(client: Client) -> None:
    """With no verifier wired (real provider gate), the surface returns 503."""
    fan = _fan()
    assert client.post("/api/fan/verify/start", headers=_auth(fan)).status_code == 503
    assert (
        client.post("/api/fan/verify/confirm", headers=_auth(fan)).status_code == 503
    )
    fan.refresh_from_db()
    assert fan.adult_verified is False
    assert fan.kyc_status == KycStatus.UNVERIFIED.value


# --- /me contract + PATCH ----------------------------------------------------


def test_me_includes_adult_and_kyc_defaults(client: Client) -> None:
    fan = _fan()
    me = client.get("/api/fan/me", headers=_auth(fan)).json()
    assert me["adult_verified"] is False
    assert me["kyc_status"] == KycStatus.UNVERIFIED.value


def test_me_reflects_verified_state(client: Client) -> None:
    fan = _fan()
    client.post("/api/fan/verify/confirm", headers=_auth(fan))
    me = client.get("/api/fan/me", headers=_auth(fan)).json()
    assert me["adult_verified"] is True
    assert me["kyc_status"] == KycStatus.VERIFIED.value


def test_patch_me_updates_own_nickname(client: Client) -> None:
    fan = _fan()
    resp = _patch(client, "/api/fan/me", {"nickname": "새닉네임"}, headers=_auth(fan))
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "새닉네임"
    fan.refresh_from_db()
    assert fan.nickname == "새닉네임"


def test_patch_me_requires_auth(client: Client) -> None:
    resp = _patch(client, "/api/fan/me", {"nickname": "x"})
    assert resp.status_code in {401, 403}


def test_patch_me_rejects_empty_nickname(client: Client) -> None:
    fan = _fan()
    resp = _patch(client, "/api/fan/me", {"nickname": ""}, headers=_auth(fan))
    assert resp.status_code == 422
