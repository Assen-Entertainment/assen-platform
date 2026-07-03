"""Tests for fan signup + digital membership card (ASS-98 v0)."""

from __future__ import annotations

import json

import pytest
from django.db import IntegrityError, transaction
from django.test import Client, override_settings
from django.utils import timezone

from apps.consent.models import ConsentKind, ConsentRecord
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.models import EventRecord
from apps.event_log.services import emit_event
from apps.identity.cookies import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from apps.identity.models import Account, AnonymousSession, Role
from apps.identity.signup_services import (
    SignupError,
    hash_phone,
    membership_card,
    normalize_phone,
    register_fan,
)
from config.otp import MockOtpSender

pytestmark = pytest.mark.django_db

_SENDER = MockOtpSender()
_PHONE = "+821012345678"


def _code(phone: str = _PHONE) -> str:
    return _SENDER.code_for(phone)


def _wrong_code(phone: str = _PHONE) -> str:
    good = _code(phone)
    return "654321" if good != "654321" else "123456"


def _emit_visit(*, fan_id: str = "", anonymous_id: str = "", visit_id: str) -> None:
    emit_event(
        event_name=EventName.VISIT_CHECKED_IN.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.FAN.value,
        source=EventSource.KIOSK.value,
        fan_id=fan_id,
        visit_id=visit_id,
        ids={"anonymous_id": anonymous_id} if anonymous_id else {},
        payload={
            "visit_id": visit_id,
            "store_id": "store-1",
            "business_day": timezone.localdate().isoformat(),
            "visit_type": "store_visit",
            "checkin_method": "qr",
            "is_verified_offline_visit": True,
        },
    )


def _account() -> Account:
    return Account.objects.get(auth_subject_hash=hash_phone(_PHONE))


# --- service: register_fan ---------------------------------------------------


def test_register_creates_fan_with_consents_and_event() -> None:
    pair = register_fan(
        phone=_PHONE,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_code(),
        otp_sender=_SENDER,
    )

    assert pair.access_token and pair.refresh_token
    account = _account()
    assert account.role == Role.FAN.value
    assert account.nickname == "미오팬"
    assert account.auth_method == "phone"
    kinds = set(ConsentRecord.objects.filter(account=account).values_list("kind", flat=True))
    assert kinds == {ConsentKind.TERMS.value, ConsentKind.PRIVACY.value}
    event = EventRecord.objects.get(
        event_name=EventName.FAN_SIGNED_UP.value, fan_id=str(account.fan_id)
    )
    # signup_method records the channel (Data_Event_Schema domain), not the provider.
    assert event.payload["signup_method"] == "web"


def test_phone_local_and_international_forms_are_one_fan() -> None:
    # 010… (KR national) and +8210… (E.164) are the same person; canonicalization
    # must yield ONE account + ONE fan_signed_up event, not two (subject-key
    # stability — otherwise the get_or_create + ledger guarantees are bypassed).
    for phone in ("01012345678", "+821012345678"):
        register_fan(
            phone=phone,
            nickname="미오팬",
            consent_terms=True,
            consent_privacy=True,
            otp_code=_SENDER.code_for(normalize_phone(phone)),
            otp_sender=_SENDER,
        )
    assert Account.objects.filter(role=Role.FAN.value).count() == 1
    assert EventRecord.objects.filter(event_name=EventName.FAN_SIGNED_UP.value).count() == 1


def test_phone_number_is_not_stored_raw() -> None:
    register_fan(
        phone=_PHONE,
        nickname="x",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_code(),
        otp_sender=_SENDER,
    )
    account = _account()
    # Only the hash persists — the raw number appears nowhere on the row.
    assert account.auth_subject_hash == hash_phone(_PHONE)
    assert _PHONE not in account.auth_subject_hash


def test_missing_consent_is_rejected() -> None:
    with pytest.raises(SignupError):
        register_fan(
            phone=_PHONE,
            nickname="x",
            consent_terms=True,
            consent_privacy=False,
            otp_code=_code(),
            otp_sender=_SENDER,
        )
    assert not Account.objects.filter(role=Role.FAN.value).exists()


def test_bad_otp_is_rejected() -> None:
    with pytest.raises(SignupError):
        register_fan(
            phone=_PHONE,
            nickname="x",
            consent_terms=True,
            consent_privacy=True,
            otp_code=_wrong_code(),
            otp_sender=_SENDER,
        )
    assert not Account.objects.filter(role=Role.FAN.value).exists()


def test_resignup_same_phone_merges_not_duplicates() -> None:
    for nick in ("a", "b"):
        register_fan(
            phone=_PHONE,
            nickname=nick,
            consent_terms=True,
            consent_privacy=True,
            otp_code=_code(),
            otp_sender=_SENDER,
        )
    accounts = Account.objects.filter(auth_subject_hash=hash_phone(_PHONE))
    assert accounts.count() == 1
    assert accounts.get().nickname == "b"  # latest nickname wins


def test_phone_normalization_merges_formats() -> None:
    norm = "+821055554444"
    register_fan(
        phone=norm,
        nickname="a",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_code(norm),
        otp_sender=_SENDER,
    )
    register_fan(
        phone="+82 10-5555-4444",  # same number, different formatting
        nickname="b",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_code(norm),
        otp_sender=_SENDER,
    )
    assert Account.objects.filter(auth_subject_hash=hash_phone(norm)).count() == 1


def test_anonymous_activity_is_merged() -> None:
    anon = AnonymousSession.objects.create()
    anon_id = str(anon.anonymous_id)
    _emit_visit(anonymous_id=anon_id, visit_id="anon-v1")

    register_fan(
        phone=_PHONE,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_code(),
        otp_sender=_SENDER,
        anonymous_id=anon_id,
    )

    anon.refresh_from_db()
    assert anon.merged_into_id == _account().id
    assert EventRecord.objects.filter(event_name=EventName.ANONYMOUS_USER_MERGED.value).exists()


# --- service: membership_card ------------------------------------------------


def test_membership_card_counts_visits() -> None:
    register_fan(
        phone=_PHONE,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_code(),
        otp_sender=_SENDER,
    )
    account = _account()
    _emit_visit(fan_id=str(account.fan_id), visit_id="v1")
    _emit_visit(fan_id=str(account.fan_id), visit_id="v2")

    card = membership_card(account)
    assert card.nickname == "미오팬"
    assert card.member_id == str(account.fan_id)
    assert card.visit_count == 2
    assert card.points == 0
    assert card.coupons == 0


def test_membership_card_excludes_voided_visits() -> None:
    register_fan(
        phone=_PHONE,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_code(),
        otp_sender=_SENDER,
    )
    account = _account()
    _emit_visit(fan_id=str(account.fan_id), visit_id="v1")
    _emit_visit(fan_id=str(account.fan_id), visit_id="v2")
    emit_event(
        event_name=EventName.VISIT_INVALIDATED.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        visit_id="v2",
        payload={"visit_id": "v2", "reason": "void"},
    )
    assert membership_card(account).visit_count == 1


# --- API ---------------------------------------------------------------------


def _signup(client: Client, **overrides: object) -> tuple[int, dict[str, object]]:
    body: dict[str, object] = {
        "phone": _PHONE,
        "otp_code": _code(),
        "nickname": "미오팬",
        "consent_terms": True,
        "consent_privacy": True,
    }
    body.update(overrides)
    response = client.post(
        "/api/fan/signup", data=json.dumps(body), content_type="application/json"
    )
    payload = response.json() if response.status_code == 200 else {}
    return response.status_code, payload


def test_signup_endpoint_issues_token(client: Client) -> None:
    status, body = _signup(client)
    assert status == 200
    assert body["access_token"]


def test_signup_endpoint_rejects_missing_consent(client: Client) -> None:
    status, _ = _signup(client, consent_privacy=False)
    assert status == 422
    assert not Account.objects.filter(role=Role.FAN.value).exists()


def test_signup_endpoint_rejects_empty_nickname(client: Client) -> None:
    status, _ = _signup(client, nickname="")
    assert status == 422
    assert not Account.objects.filter(role=Role.FAN.value).exists()


def test_otp_endpoint_acks_without_leaking_code(client: Client) -> None:
    response = client.post(
        "/api/fan/signup/otp",
        data=json.dumps({"phone": _PHONE}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert _code() not in json.dumps(response.json())


def test_membership_card_endpoint_requires_auth(client: Client) -> None:
    assert client.get("/api/fan/membership-card").status_code in {401, 403}


def test_membership_card_endpoint_returns_card(client: Client) -> None:
    _, body = _signup(client)
    token = body["access_token"]
    response = client.get(
        "/api/fan/membership-card",
        headers={"authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["nickname"] == "미오팬"
    assert body["visit_count"] == 0


# --- Codex fixes: uniqueness, fail-closed OTP, phone validation, no public merge


def test_auth_subject_hash_is_unique_when_set() -> None:
    # The partial unique constraint stops a concurrent re-signup from creating a
    # duplicate fan for the same phone-hash (race that filter()+create() missed).
    subject = hash_phone(_PHONE)
    Account.objects.create(role=Role.FAN.value, auth_subject_hash=subject)
    with pytest.raises(IntegrityError), transaction.atomic():
        Account.objects.create(role=Role.FAN.value, auth_subject_hash=subject)


def test_blank_auth_subject_hash_allows_duplicates() -> None:
    # The constraint is partial (non-empty only), so staff rows — which never set
    # a phone-hash — coexist with the default "".
    Account.objects.create(role=Role.OPERATOR.value, auth_subject_hash="")
    Account.objects.create(role=Role.MANAGER.value, auth_subject_hash="")
    assert Account.objects.filter(auth_subject_hash="").count() == 2


@override_settings(ENABLE_MOCK_FAN_OTP=False)
def test_signup_unavailable_when_otp_disabled(client: Client) -> None:
    # Fail-closed: with no OTP provider wired, signup must refuse — never accept a
    # reproducible mock code as if it were a verified factor.
    status, _ = _signup(client)
    assert status == 503
    assert not Account.objects.filter(role=Role.FAN.value).exists()


@override_settings(ENABLE_MOCK_FAN_OTP=False)
def test_otp_endpoint_unavailable_when_disabled(client: Client) -> None:
    response = client.post(
        "/api/fan/signup/otp",
        data=json.dumps({"phone": _PHONE}),
        content_type="application/json",
    )
    assert response.status_code == 503


def test_request_otp_rejects_junk_phone(client: Client) -> None:
    response = client.post(
        "/api/fan/signup/otp",
        data=json.dumps({"phone": "abc"}),
        content_type="application/json",
    )
    assert response.status_code == 422


def test_signup_rejects_junk_phone(client: Client) -> None:
    status, _ = _signup(client, phone="abc")
    assert status == 422
    assert not Account.objects.filter(role=Role.FAN.value).exists()


def test_signup_ignores_anonymous_id_in_body(client: Client) -> None:
    # anonymous_id is no longer a public field: an unverified body claim must not
    # drive a merge of someone else's pre-signup activity. Extra keys are ignored.
    anon = AnonymousSession.objects.create()
    status, _ = _signup(client, anonymous_id=str(anon.anonymous_id))
    assert status == 200
    anon.refresh_from_db()
    assert anon.merged_into_id is None
    assert not EventRecord.objects.filter(event_name=EventName.ANONYMOUS_USER_MERGED.value).exists()


def test_resignup_does_not_reemit_fan_signed_up() -> None:
    # fan_signed_up feeds the new-signup KPI (ASS-112); a re-signup returns the
    # existing account, so the append-only ledger must not gain a 2nd creation
    # event — otherwise the signup count inflates permanently.
    for _ in range(2):
        register_fan(
            phone=_PHONE,
            nickname="미오팬",
            consent_terms=True,
            consent_privacy=True,
            otp_code=_code(),
            otp_sender=_SENDER,
        )
    assert EventRecord.objects.filter(event_name=EventName.FAN_SIGNED_UP.value).count() == 1


# --- Dual-surface token delivery (ADR-0002: app = JSON body, web = httpOnly cookie)


def test_app_signup_returns_tokens_in_body() -> None:
    client = Client()
    status, body = _signup(client)  # web defaults False → app surface
    assert status == 200
    assert body["token_delivery"] == "body"
    assert body["access_token"] and body["refresh_token"]
    # The app surface sets no auth cookies (it stores tokens in secure storage).
    assert ACCESS_COOKIE_NAME not in client.cookies


def test_web_signup_sets_httponly_cookies_not_body() -> None:
    client = Client()
    status, body = _signup(client, web=True)
    assert status == 200
    # No secret in the JS-readable body — tokens are delivered as cookies.
    assert body["token_delivery"] == "cookie"
    assert body["access_token"] == ""
    assert body["refresh_token"] == ""
    assert client.cookies[ACCESS_COOKIE_NAME]["httponly"]
    refresh = client.cookies[REFRESH_COOKIE_NAME]
    assert refresh["httponly"]
    # Refresh is path-scoped to the fan surface (A2 broadened it from /refresh so
    # logout can read it) + SameSite=Strict.
    assert refresh["path"] == "/api/fan"
    assert refresh["samesite"].lower() == "strict"


def test_web_signup_card_authenticates_via_cookie() -> None:
    client = Client()
    _signup(client, web=True)  # sets the access cookie on the client jar
    response = client.get("/api/fan/membership-card")  # no Authorization header
    assert response.status_code == 200
    assert response.json()["nickname"] == "미오팬"
