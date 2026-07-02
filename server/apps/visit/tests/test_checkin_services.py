"""Service tests for rotating QR check-in tokens (ASS-99).

Prove the CONSTRAINTS #18 controls: a token is single-use (no replay), expires
(rotation/anti-screenshot), a fresh issue supersedes the fan's live tokens, the
plaintext is hashed at rest, issuance is fan-only, and a blocked fan cannot
check in. Redemption records a genuine fan visit — the canonical
``visit_checked_in`` event with ``actor_is_operator=False`` / ``checkin_method=qr``.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.event_log.services import count_msfc_starts
from apps.identity.models import Account, Role
from apps.safety.models import BlockReason, BlockScope, UserBlock
from apps.visit.checkin_services import (
    _hash_token,
    issue_checkin_token,
    redeem_checkin_token,
)
from apps.visit.models import CheckinToken, VisitRecord, VisitRecordSource

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _block(fan: Account, operator: Account, scope: str) -> UserBlock:
    """Create an active hard block on [fan] for [scope]."""
    return UserBlock.objects.create(
        target=fan,
        block_scope=scope,
        block_reason=BlockReason.SAFETY_RISK.value,
        effective_from=timezone.now(),
        created_by=operator,
    )


def test_issue_returns_plaintext_and_stores_only_the_hash() -> None:
    """Issue returns a future-dated pending token; only the hash is persisted."""
    fan = _account(Role.FAN.value)
    token, raw = issue_checkin_token(fan=fan)
    assert token.redeemed_at is None
    assert token.expires_at > timezone.now()
    assert token.fan_id == fan.pk
    # The plaintext is never stored; the row carries only its hash.
    assert token.token_hash == _hash_token(raw)
    assert not CheckinToken.objects.filter(token_hash=raw).exists()


def test_issue_supersedes_prior_live_tokens() -> None:
    """Rotation: issuing a new token expires the fan's earlier pending one."""
    fan = _account(Role.FAN.value)
    first, _ = issue_checkin_token(fan=fan)
    second, _ = issue_checkin_token(fan=fan)

    first.refresh_from_db()
    assert first.expires_at <= timezone.now()
    assert second.expires_at > timezone.now()


def test_issue_rejects_non_fan() -> None:
    """A token is only meaningful for a fan; issuing for staff is refused."""
    operator = _account(Role.OPERATOR.value)
    with pytest.raises(ValueError):
        issue_checkin_token(fan=operator)


def test_redeem_records_qr_visit_and_marks_token() -> None:
    """Redeeming records a fan visit, emits the canonical event, marks the token."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    _token, raw = issue_checkin_token(fan=fan)

    record, redeemed = redeem_checkin_token(token=raw, operator=operator)

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
    token, raw = issue_checkin_token(fan=fan)
    CheckinToken.objects.filter(pk=token.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    with pytest.raises(ValueError):
        redeem_checkin_token(token=raw, operator=operator)
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
    _token, raw = issue_checkin_token(fan=fan)

    redeem_checkin_token(token=raw, operator=operator)
    with pytest.raises(ValueError):
        redeem_checkin_token(token=raw, operator=operator)

    assert VisitRecord.objects.count() == 1


def test_redeem_blocked_fan_rejected() -> None:
    """A fan with an active store-visit block cannot check in (safety)."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    _block(fan, operator, BlockScope.STORE_VISIT.value)
    _token, raw = issue_checkin_token(fan=fan)

    with pytest.raises(ValueError):
        redeem_checkin_token(token=raw, operator=operator)
    # No visit is recorded for a blocked fan, so MSFC never sees it.
    assert VisitRecord.objects.count() == 0
    assert count_msfc_starts() == 0


def test_redeem_blocked_all_scope_rejected() -> None:
    """An ``all``-scope block also blocks store check-in."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    _block(fan, operator, BlockScope.ALL.value)
    _token, raw = issue_checkin_token(fan=fan)

    with pytest.raises(ValueError):
        redeem_checkin_token(token=raw, operator=operator)
    assert VisitRecord.objects.count() == 0
