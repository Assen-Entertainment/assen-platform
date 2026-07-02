"""Tests for the coupon + point service (F09, ASS-108 v0).

Covers the coupon lifecycle (issue/redeem/cancel/expire, blocked-fan refusal,
expiry guard, status guards), the canonical coupon_* emissions, and the point
ledger (grant/adjust, non-negative balance, point_* emissions).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.coupon.models import Coupon, CouponStatus, CouponType
from apps.coupon.services import (
    adjust_points,
    cancel_coupon,
    expire_coupon,
    grant_points,
    issue_coupon,
    point_balance,
    redeem_coupon,
)
from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account, Role
from apps.safety.models import BlockScope, UserBlock

pytestmark = pytest.mark.django_db

REVISIT = CouponType.REVISIT.value


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _operator() -> Account:
    """Create an operator account."""
    return _account(Role.OPERATOR.value)


def _fan() -> Account:
    """Create a fan account."""
    return _account(Role.FAN.value)


def _issue(op: Account, fan: Account) -> Coupon:
    """Issue a revisit coupon to a fan."""
    return issue_coupon(fan=fan, coupon_type=REVISIT, actor=op)


def test_issue_creates_active_and_emits() -> None:
    """Issuing a coupon yields an active coupon and a coupon_issued event."""
    op, fan = _operator(), _fan()
    coupon = _issue(op, fan)
    assert coupon.status == CouponStatus.ACTIVE.value
    assert EventRecord.objects.filter(event_name=EventName.COUPON_ISSUED.value).count() == 1


def test_issue_rejects_non_fan_and_unknown_type() -> None:
    """A non-fan subject and an unknown coupon type are both refused."""
    op = _operator()
    with pytest.raises(ValueError):
        issue_coupon(fan=op, coupon_type=REVISIT, actor=op)
    with pytest.raises(ValueError):
        issue_coupon(fan=_fan(), coupon_type="nope", actor=op)


def test_redeem_mints_redemption_id_and_emits() -> None:
    """Redeeming an active coupon sets redeemed status + a redemption id + event."""
    op, fan = _operator(), _fan()
    coupon = redeem_coupon(coupon=_issue(op, fan), actor=op)
    assert coupon.status == CouponStatus.REDEEMED.value
    assert coupon.redemption_id is not None
    ev = EventRecord.objects.get(event_name=EventName.COUPON_REDEEMED.value)
    assert ev.payload["redemption_status"] == "redeemed"
    assert ev.payload["coupon_redemption_id"] == str(coupon.redemption_id)


def test_redeem_twice_is_refused() -> None:
    """A redeemed coupon cannot be redeemed again (status guard)."""
    op, fan = _operator(), _fan()
    coupon = redeem_coupon(coupon=_issue(op, fan), actor=op)
    with pytest.raises(ValueError):
        redeem_coupon(coupon=Coupon.objects.get(pk=coupon.pk), actor=op)


def test_blocked_fan_cannot_redeem() -> None:
    """A fan blocked from fandom features cannot redeem (fail-closed)."""
    op, fan = _operator(), _fan()
    UserBlock.objects.create(
        target=fan,
        block_scope=BlockScope.FANDOM_FEATURE.value,
        block_reason="policy_violation",
        effective_from=timezone.now(),
        created_by=_account(Role.MANAGER.value),
    )
    with pytest.raises(ValueError):
        redeem_coupon(coupon=_issue(op, fan), actor=op)


def test_expired_coupon_cannot_be_redeemed() -> None:
    """A coupon past its expiry is refused at redeem."""
    op, fan = _operator(), _fan()
    coupon = issue_coupon(
        fan=fan, coupon_type=REVISIT, actor=op, expires_at=timezone.now() - timedelta(days=1)
    )
    with pytest.raises(ValueError):
        redeem_coupon(coupon=coupon, actor=op)


def test_cancel_and_expire_emit_and_guard_status() -> None:
    """Cancel/expire emit their events and reject invalid source states."""
    op, fan = _operator(), _fan()
    cancelled = cancel_coupon(coupon=_issue(op, fan), actor=op)
    assert cancelled.status == CouponStatus.CANCELLED.value
    assert EventRecord.objects.filter(event_name=EventName.COUPON_CANCELLED.value).count() == 1
    with pytest.raises(ValueError):
        expire_coupon(coupon=Coupon.objects.get(pk=cancelled.pk), actor=op)  # not active

    expired = expire_coupon(coupon=_issue(op, fan), actor=op)
    assert expired.status == CouponStatus.EXPIRED.value
    assert EventRecord.objects.filter(event_name=EventName.COUPON_EXPIRED.value).count() == 1


def test_grant_and_balance_and_point_event() -> None:
    """Granting points moves the balance and emits point_granted."""
    op, fan = _operator(), _fan()
    grant_points(fan=fan, delta=30, actor=op, reason="first visit")
    assert point_balance(fan) == 30
    assert EventRecord.objects.filter(event_name=EventName.POINT_GRANTED.value).count() == 1


def test_grant_rejects_non_positive_and_non_fan() -> None:
    """Grant requires a positive delta and a fan subject."""
    op, fan = _operator(), _fan()
    with pytest.raises(ValueError):
        grant_points(fan=fan, delta=0, actor=op)
    with pytest.raises(ValueError):
        grant_points(fan=op, delta=10, actor=op)


def test_adjust_cannot_drive_balance_negative() -> None:
    """A negative adjustment is refused when it would underflow the balance."""
    op, fan = _operator(), _fan()
    grant_points(fan=fan, delta=10, actor=op)
    with pytest.raises(ValueError):
        adjust_points(fan=fan, delta=-25, actor=op)
    adjust_points(fan=fan, delta=-4, actor=op)
    assert point_balance(fan) == 6
    assert EventRecord.objects.filter(event_name=EventName.POINT_ADJUSTED.value).count() == 1


def test_adjust_rejects_zero() -> None:
    """A zero adjustment is refused."""
    op, fan = _operator(), _fan()
    with pytest.raises(ValueError):
        adjust_points(fan=fan, delta=0, actor=op)


def test_grant_is_idempotent_on_reference() -> None:
    """A retry with the same reference returns the first entry, not a second post."""
    from apps.coupon.models import PointEntry

    op, fan = _operator(), _fan()
    first = grant_points(fan=fan, delta=20, actor=op, reference="visit-42")
    again = grant_points(fan=fan, delta=20, actor=op, reference="visit-42")
    assert again.id == first.id
    assert point_balance(fan) == 20  # not doubled
    assert PointEntry.objects.filter(fan=fan).count() == 1
    assert EventRecord.objects.filter(event_name=EventName.POINT_GRANTED.value).count() == 1


def test_unreferenced_grants_are_not_deduped() -> None:
    """Two grants without a reference are distinct entries (no false dedup)."""
    from apps.coupon.models import PointEntry

    op, fan = _operator(), _fan()
    grant_points(fan=fan, delta=5, actor=op)
    grant_points(fan=fan, delta=5, actor=op)
    assert PointEntry.objects.filter(fan=fan).count() == 2
    assert point_balance(fan) == 10
