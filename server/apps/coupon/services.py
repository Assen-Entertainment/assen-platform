"""Service layer for coupons + points (F09, ASS-108 v0).

Every mutation passes through this module so the operational row, the audit
trail, and the append-only analytics events stay coupled. Analytics events are
emitted **only** through :func:`apps.event_log.services.emit_event` (the validated
registry): ``coupon_issued`` / ``coupon_redeemed`` / ``coupon_cancelled`` /
``coupon_expired`` and ``point_granted`` / ``point_adjusted``.

No discount/money figure is stored (the coupon value is the approval-gated,
deferred slice). A blocked fan cannot redeem (fail-closed, FANDOM_FEATURE), and
point adjustments cannot drive a balance negative.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from django.db import IntegrityError, models, transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.coupon.models import (
    DEFAULT_STORE_ID,
    Coupon,
    CouponStatus,
    CouponType,
    PointEntry,
)
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import emit_event
from apps.identity.models import Account, Role
from apps.safety.models import BlockScope
from apps.safety.services import has_active_block

# Scopes that bar a fan from redeeming a coupon (F11: 팬덤 기능 제한).
_REDEEM_BLOCK_SCOPES = [BlockScope.FANDOM_FEATURE.value]


# --------------------------------------------------------------------------- #
# Coupon lifecycle
# --------------------------------------------------------------------------- #
@transaction.atomic
def issue_coupon(
    *,
    fan: Account,
    coupon_type: str,
    actor: Account,
    expires_at: datetime | None = None,
    store_id: str = DEFAULT_STORE_ID,
) -> Coupon:
    """Issue an active coupon to ``fan`` and emit coupon_issued."""
    if fan.role != Role.FAN.value:
        raise ValueError("Coupons can only be issued to fan accounts.")
    _validate_enum(coupon_type, CouponType, "coupon_type")
    coupon = Coupon.objects.create(
        fan=fan,
        coupon_type=coupon_type,
        store_id=store_id,
        expires_at=expires_at,
        issued_by=actor,
    )
    _emit_coupon(coupon, EventName.COUPON_ISSUED.value, actor)
    _audit_coupon(actor, AuditAction.COUPON_ISSUED.value, coupon)
    return coupon


@transaction.atomic
def redeem_coupon(*, coupon: Coupon, actor: Account, visit_id: str = "") -> Coupon:
    """Redeem an active coupon, minting its redemption id and emitting coupon_redeemed.

    Fail-closed: a fan blocked from fandom features cannot redeem (the block is on
    the subject fan, so an operator acting on their behalf is refused too).
    """
    coupon = _lock(coupon)
    if coupon.status != CouponStatus.ACTIVE.value:
        raise ValueError(f"Cannot redeem a coupon in status '{coupon.status}'.")
    if coupon.expires_at is not None and coupon.expires_at <= timezone.now():
        raise ValueError("Coupon has expired.")
    if has_active_block(target=coupon.fan, scopes=_REDEEM_BLOCK_SCOPES):
        raise ValueError("Fan is blocked from redeeming coupons.")
    coupon.status = CouponStatus.REDEEMED.value
    coupon.redemption_id = uuid.uuid4()
    coupon.redeemed_at = timezone.now()
    coupon.save(update_fields=["status", "redemption_id", "redeemed_at", "updated_at"])
    _emit_coupon(
        coupon,
        EventName.COUPON_REDEEMED.value,
        actor,
        extra={
            "coupon_redemption_id": str(coupon.redemption_id),
            "redemption_status": "redeemed",
        },
        ids_extra={"coupon_redemption_id": str(coupon.redemption_id)},
        visit_id=visit_id,
    )
    _audit_coupon(actor, AuditAction.COUPON_REDEEMED.value, coupon)
    return coupon


@transaction.atomic
def cancel_coupon(*, coupon: Coupon, actor: Account) -> Coupon:
    """Cancel/void a coupon (active or redeemed) and emit coupon_cancelled."""
    coupon = _lock(coupon)
    if coupon.status not in (CouponStatus.ACTIVE.value, CouponStatus.REDEEMED.value):
        raise ValueError(f"Cannot cancel a coupon in status '{coupon.status}'.")
    coupon.status = CouponStatus.CANCELLED.value
    coupon.save(update_fields=["status", "updated_at"])
    _emit_coupon(coupon, EventName.COUPON_CANCELLED.value, actor)
    _audit_coupon(actor, AuditAction.COUPON_CANCELLED.value, coupon)
    return coupon


@transaction.atomic
def expire_coupon(*, coupon: Coupon, actor: Account) -> Coupon:
    """Expire an active coupon and emit coupon_expired."""
    coupon = _lock(coupon)
    if coupon.status != CouponStatus.ACTIVE.value:
        raise ValueError(f"Cannot expire a coupon in status '{coupon.status}'.")
    coupon.status = CouponStatus.EXPIRED.value
    coupon.save(update_fields=["status", "updated_at"])
    _emit_coupon(coupon, EventName.COUPON_EXPIRED.value, actor)
    _audit_coupon(actor, AuditAction.COUPON_EXPIRED.value, coupon)
    return coupon


# --------------------------------------------------------------------------- #
# Point ledger
# --------------------------------------------------------------------------- #
@transaction.atomic
def grant_points(
    *, fan: Account, delta: int, actor: Account, reason: str = "", reference: str = ""
) -> PointEntry:
    """Grant points to a fan (delta must be positive) and emit point_granted."""
    if delta <= 0:
        raise ValueError("Granted points must be positive.")
    return _add_point_entry(
        fan=fan,
        delta=delta,
        actor=actor,
        reason=reason,
        reference=reference,
        event_name=EventName.POINT_GRANTED.value,
        action=AuditAction.POINT_GRANTED.value,
    )


@transaction.atomic
def adjust_points(
    *, fan: Account, delta: int, actor: Account, reason: str = "", reference: str = ""
) -> PointEntry:
    """Apply a manual point correction and emit point_adjusted.

    ``delta`` may be negative but must not drive the balance below zero
    (fail-closed); a per-fan row lock serialises concurrent adjustments.
    """
    if delta == 0:
        raise ValueError("A point adjustment must be non-zero.")
    return _add_point_entry(
        fan=fan,
        delta=delta,
        actor=actor,
        reason=reason,
        reference=reference,
        event_name=EventName.POINT_ADJUSTED.value,
        action=AuditAction.POINT_ADJUSTED.value,
    )


def point_balance(fan: Account) -> int:
    """Return the fan's current point balance (sum of ledger deltas)."""
    total = PointEntry.objects.filter(fan=fan).aggregate(total=models.Sum("delta"))["total"]
    return int(total or 0)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _add_point_entry(
    *,
    fan: Account,
    delta: int,
    actor: Account,
    reason: str,
    reference: str,
    event_name: str,
    action: str,
) -> PointEntry:
    """Append a point entry under a per-fan lock; refuse a negative resulting balance.

    Idempotent on ``reference``: a retry with the same (fan, reference) returns the
    existing entry without re-posting (so a network retry cannot double the
    balance). The per-fan row lock serialises the check, and the partial-unique
    constraint is the cross-transaction backstop.
    """
    if fan.role != Role.FAN.value:
        raise ValueError("Points can only be recorded for fan accounts.")
    if len(reason) > 200:
        raise ValueError("reason is too long.")
    if len(reference) > 100:
        raise ValueError("reference is too long.")
    # Serialise point mutations for this fan so the balance check cannot race.
    Account.objects.select_for_update().get(pk=fan.pk)
    if reference:
        existing = PointEntry.objects.filter(fan=fan, reference=reference).first()
        if existing is not None:
            return existing  # idempotent replay: no new row, event, or audit
    if point_balance(fan) + delta < 0:
        raise ValueError("A point adjustment must not make the balance negative.")
    try:
        with transaction.atomic():
            entry = PointEntry.objects.create(
                fan=fan, delta=delta, reason=reason.strip(), reference=reference, created_by=actor
            )
    except IntegrityError:
        # Lost the race on the same reference: return the entry that won.
        existing = PointEntry.objects.filter(fan=fan, reference=reference).first()
        if existing is not None:
            return existing
        raise
    emit_event(
        event_name=event_name,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_id=str(actor.fan_id),
        fan_id=str(fan.fan_id),
        actor_is_operator=True,
        ids={"point_entry_id": str(entry.id)},
        payload={"fan_id": str(fan.fan_id), "point_entry_id": str(entry.id), "delta": delta},
    )
    record_audit(
        actor=actor,
        action=action,
        target=str(entry.id),
        metadata={"fan_id": str(fan.fan_id), "delta": delta},
    )
    return entry


def _lock(coupon: Coupon) -> Coupon:
    """Re-load the coupon under a row lock so concurrent transitions serialise."""
    return Coupon.objects.select_for_update().get(pk=coupon.pk)


def _emit_coupon(
    coupon: Coupon,
    event_name: str,
    actor: Account,
    *,
    extra: dict[str, str] | None = None,
    ids_extra: dict[str, str] | None = None,
    visit_id: str = "",
) -> None:
    """Emit a coupon_* analytics signal through the validated funnel (no PII)."""
    is_operator = actor.role != Role.FAN.value
    fan_id = str(coupon.fan.fan_id)
    ids: dict[str, str] = {"coupon_id": str(coupon.id)}
    if ids_extra:
        ids.update(ids_extra)
    if visit_id:
        ids["visit_id"] = visit_id
    payload: dict[str, object] = {
        "fan_id": fan_id,
        "coupon_id": str(coupon.id),
        "coupon_type": coupon.coupon_type,
    }
    if extra:
        payload.update(extra)
    emit_event(
        event_name=event_name,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value if is_operator else ActorType.FAN.value,
        source=EventSource.MANUAL.value if is_operator else EventSource.FAN_APP.value,
        actor_id=str(actor.fan_id),
        fan_id=fan_id,
        actor_is_operator=is_operator,
        ids=ids,
        context={"store_id": coupon.store_id},
        payload=payload,
    )


def _audit_coupon(actor: Account, action: str, coupon: Coupon) -> None:
    """Write the audit entry for an operator coupon mutation."""
    record_audit(
        actor=actor,
        action=action,
        target=str(coupon.id),
        metadata={"coupon_type": coupon.coupon_type, "status": coupon.status},
    )


def _validate_enum(value: str, choices: type[models.TextChoices], field: str) -> None:
    """Raise ``ValueError`` if ``value`` is not a member of ``choices`` (no echo)."""
    if value not in choices.values:
        raise ValueError(f"Unknown {field}.")
