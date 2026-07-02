"""Tests for QR check-in operational hardening (ASS-151): reaper + throttle."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.visit.checkin_services import (
    _ISSUE_MAX,
    CheckinThrottled,
    issue_checkin_token,
)
from apps.visit.models import CheckinToken
from apps.visit.tasks import purge_expired_checkin_tokens

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def test_purge_removes_only_long_expired_unredeemed_tokens() -> None:
    """The reaper deletes unredeemed long-expired tokens, keeping the rest."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    now = timezone.now()

    old_unredeemed = CheckinToken.objects.create(
        fan=fan, token_hash="h_old", expires_at=now - timedelta(hours=2)
    )
    recent_unredeemed = CheckinToken.objects.create(
        fan=fan, token_hash="h_recent", expires_at=now - timedelta(minutes=10)
    )
    redeemed_old = CheckinToken.objects.create(
        fan=fan,
        token_hash="h_redeemed",
        expires_at=now - timedelta(hours=2),
        redeemed_at=now - timedelta(hours=2),
        redeemed_by=operator,
    )
    fresh = CheckinToken.objects.create(
        fan=fan, token_hash="h_fresh", expires_at=now + timedelta(seconds=30)
    )

    deleted = purge_expired_checkin_tokens()

    assert deleted == 1
    assert not CheckinToken.objects.filter(pk=old_unredeemed.pk).exists()
    # Recently-expired (grace), redeemed (audit), and live tokens are kept.
    surviving = set(CheckinToken.objects.values_list("pk", flat=True))
    assert surviving == {recent_unredeemed.pk, redeemed_old.pk, fresh.pk}


def test_issue_is_throttled_after_the_cap_in_the_window() -> None:
    """Up to _ISSUE_MAX issues in the window succeed; the next is throttled."""
    fan = _account(Role.FAN.value)
    for _ in range(_ISSUE_MAX):
        issue_checkin_token(fan=fan)
    with pytest.raises(CheckinThrottled):
        issue_checkin_token(fan=fan)


def test_issue_endpoint_returns_429_when_throttled(client: Client) -> None:
    """The token endpoint maps the throttle to HTTP 429."""
    fan = _account(Role.FAN.value)
    for _ in range(_ISSUE_MAX):
        issue_checkin_token(fan=fan)
    response = client.post("/api/checkin/token", headers=_auth(fan))
    assert response.status_code == 429


def test_issue_resumes_after_the_window_slides() -> None:
    """Issues age out of the window, so a throttled fan can issue again later."""
    fan = _account(Role.FAN.value)
    for _ in range(_ISSUE_MAX):
        issue_checkin_token(fan=fan)
    # Backdate the in-window issues past the throttle window (auto_now_add only
    # applies on insert, so .update bypasses it for the test).
    CheckinToken.objects.filter(fan=fan).update(
        issued_at=timezone.now() - timedelta(seconds=120)
    )
    token, _raw = issue_checkin_token(fan=fan)
    assert token.pk is not None
