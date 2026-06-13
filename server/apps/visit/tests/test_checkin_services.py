"""Service tests for rotating QR check-in tokens (ASS-99).

Prove the CONSTRAINTS #18 controls: a token is single-use (no replay), expires
(rotation/anti-screenshot), and a fresh issue supersedes the fan's live tokens.
Redemption records a genuine fan visit — the canonical ``visit_checked_in``
event with ``actor_is_operator=False`` and ``checkin_method=qr``.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.event_log.services import count_msfc_starts
from apps.identity.models import Account, Role
from apps.visit.checkin_services import issue_checkin_token, redeem_checkin_token
from apps.visit.models import CheckinToken, VisitRecord, VisitRecordSource

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def test_issue_creates_unredeemed_token_with_future_expiry() -> None:
    """A freshly issued token is pending and expires in the future."""
    fan = _account(Role.FAN.value)
    token = issue_checkin_token(fan=fan)
    assert token.redeemed_at is None
    assert token.expires_at > timezone.now()
    assert token.fan_id == fan.pk


def test_issue_supersedes_prior_live_tokens() -> None:
    """Rotation: issuing a new token expires the fan's earlier pending one."""
    fan = _account(Role.FAN.value)
    first = issue_checkin_token(fan=fan)
    second = issue_checkin_token(fan=fan)

    first.refresh_from_db()
    # The earlier QR is dead even though its original TTL had not elapsed.
    assert first.expires_at <= timezone.now()
    assert second.expires_at > timezone.now()


def test_redeem_records_qr_visit_and_marks_token() -> None:
    """Redeeming records a fan visit, emits the canonical event, marks the token."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    token = issue_checkin_token(fan=fan)

    record, redeemed = redeem_checkin_token(token=token.token, operator=operator)

    assert record.source == VisitRecordSource.QR_SELF.value
    assert record.fan_id == fan.pk
    assert record.created_by_id == operator.pk  # operator scan = provenance
    assert redeemed.redeemed_at is not None
    assert redeemed.redeemed_by_id == operator.pk
    assert redeemed.visit_id == record.id

    event = EventRecord.objects.get(event_name=EventName.VISIT_CHECKED_IN.value)
    assert event.fan_id == str(fan.fan_id)
    assert event.visit_id == str(record.id)
    # A QR self-check-in is a genuine fan visit: it counts toward MSFC.
    assert event.actor_is_operator is False
    assert event.payload["checkin_method"] == "qr"
    assert count_msfc_starts() == 1


def test_redeem_invalid_token_rejected() -> None:
    """An unknown token is rejected and records no visit."""
    operator = _account(Role.OPERATOR.value)
    with pytest.raises(ValueError):
        redeem_checkin_token(token="not-a-real-token", operator=operator)
    assert VisitRecord.objects.count() == 0


def test_redeem_expired_token_rejected() -> None:
    """An expired token is rejected (rotation / anti-screenshot)."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    token = issue_checkin_token(fan=fan)
    # Force expiry without waiting on the wall clock.
    CheckinToken.objects.filter(pk=token.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    with pytest.raises(ValueError):
        redeem_checkin_token(token=token.token, operator=operator)
    assert VisitRecord.objects.count() == 0


def test_redeem_is_single_use() -> None:
    """A token redeems at most once; a replay is rejected (one visit only).

    This exercises the ``redeemed_at`` guard sequentially. The concurrent
    double-redeem race is additionally guarded by ``select_for_update`` in
    ``redeem_checkin_token``, but that row lock is a no-op on the SQLite test DB —
    it only takes effect on Postgres (prod/dev), so it is not asserted here.
    """
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    token = issue_checkin_token(fan=fan)

    redeem_checkin_token(token=token.token, operator=operator)
    with pytest.raises(ValueError):
        redeem_checkin_token(token=token.token, operator=operator)

    assert VisitRecord.objects.count() == 1
