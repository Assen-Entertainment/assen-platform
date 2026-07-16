"""Tests for the digital membership card + phone-identity account row (ASS-98 v0).

Phone-OTP signup was retired in favour of email/social auth (auth redesign), so this
suite covers the retained surface of ``signup_services``: the ``membership_card`` read
model and the ``/fan/membership-card`` endpoint, plus the partial-unique
``auth_subject_hash`` constraint that still guards the phone-identity row. Accounts are
created directly (no signup endpoint).
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction
from django.test import Client
from django.utils import timezone

from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import emit_event
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.identity.signup_services import hash_phone, membership_card

pytestmark = pytest.mark.django_db

_PHONE = "+821012345678"


def _fan_account(nickname: str = "미오팬") -> Account:
    """Create a fan account directly (phone-OTP signup was retired)."""
    return Account.objects.create(
        role=Role.FAN.value,
        auth_subject_hash=hash_phone(_PHONE),
        nickname=nickname,
        auth_method="phone",
    )


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


# --- service: membership_card ------------------------------------------------


def test_membership_card_counts_visits() -> None:
    account = _fan_account()
    _emit_visit(fan_id=str(account.fan_id), visit_id="v1")
    _emit_visit(fan_id=str(account.fan_id), visit_id="v2")

    card = membership_card(account)
    assert card.nickname == "미오팬"
    assert card.member_id == str(account.fan_id)
    assert card.visit_count == 2
    assert card.points == 0
    assert card.coupons == 0


def test_membership_card_excludes_voided_visits() -> None:
    account = _fan_account()
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


# --- API: /fan/membership-card -----------------------------------------------


def test_membership_card_endpoint_requires_auth(client: Client) -> None:
    assert client.get("/api/fan/membership-card").status_code in {401, 403}


def test_membership_card_endpoint_returns_card(client: Client) -> None:
    account = _fan_account()
    token = issue_token_pair(account).access_token
    response = client.get(
        "/api/fan/membership-card",
        headers={"authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["nickname"] == "미오팬"
    assert body["visit_count"] == 0


# --- auth_subject_hash partial-unique constraint -----------------------------


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
