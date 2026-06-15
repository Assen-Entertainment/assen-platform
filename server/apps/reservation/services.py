"""Service layer for reservation/waitlist lifecycle (F03, ASS-109 v0).

Every reservation mutation passes through this module so the operational row,
the audit trail, and the append-only analytics event stay coupled. Analytics
events are emitted **only** through :func:`apps.event_log.services.emit_event`
(the validated registry) — mirrors the visit/cheki/pos_lite domains.

Event mapping (Data_Event_Schema):

- create  → ``reservation_created``
- cancel  → ``reservation_cancelled``
- confirm/change/no-show → **audit only** (no event registered; no-show is an
  operational status, not an analytics signal in the P0 registry).

Block enforcement: a fan with an active ``BlockScope.RESERVATION`` (or ``ALL``)
block is refused at ``create`` — the enforcement surface ASS-111 deferred to F03
(F11: "차단된 팬은 예약 기능 접근이 제한된다"). The check is applied to the
subject fan regardless of who records the reservation (fail-closed).

Out of scope for v0 (held): prepaid reservations, seat assignment, and
external-store / 네이버 예약 sync (operational form open question).
"""

from __future__ import annotations

from datetime import date, time

from django.db import models, transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import emit_event
from apps.identity.models import Account, Role
from apps.reservation.models import (
    DEFAULT_STORE_ID,
    Reservation,
    ReservationStatus,
    ReservationType,
)
from apps.safety.models import BlockScope
from apps.safety.services import has_active_block

# A reservation can still be confirmed/changed/cancelled while in these states.
_ACTIVE_STATUSES = (ReservationStatus.REQUESTED.value, ReservationStatus.CONFIRMED.value)
# Guardrail against absurd / abusive party sizes; single small café (R0.1).
_MAX_PARTY_SIZE = 20


@transaction.atomic
def create_reservation(
    *,
    fan: Account,
    actor: Account,
    reserved_date: date,
    reserved_time: time | None = None,
    party_size: int = 1,
    reservation_type: str = ReservationType.RESERVATION.value,
    store_id: str = DEFAULT_STORE_ID,
    operator_note: str = "",
) -> Reservation:
    """Register a reservation/waitlist entry for ``fan`` and emit its event.

    ``actor`` is whoever records it (the fan from the app, or an operator on the
    fan's behalf). Rejects a non-fan subject, a blocked fan, an out-of-domain
    type, an out-of-range party size, a past date, and an exact duplicate active
    slot (double-submit guard).
    """
    if fan.role != Role.FAN.value:
        raise ValueError("Reservations can only be created for fan accounts.")
    if has_active_block(target=fan, scopes=[BlockScope.RESERVATION.value]):
        raise ValueError("Fan is blocked from making reservations.")
    _validate_enum(reservation_type, ReservationType, "reservation_type")
    if party_size < 1 or party_size > _MAX_PARTY_SIZE:
        raise ValueError(f"party_size must be between 1 and {_MAX_PARTY_SIZE}.")
    if reserved_date < timezone.localdate():
        raise ValueError("reserved_date must not be in the past.")
    if Reservation.objects.filter(
        fan=fan,
        reserved_date=reserved_date,
        reserved_time=reserved_time,
        reservation_type=reservation_type,
        status__in=_ACTIVE_STATUSES,
    ).exists():
        raise ValueError("An active reservation for this slot already exists.")

    reservation = Reservation.objects.create(
        fan=fan,
        store_id=store_id,
        reservation_type=reservation_type,
        reserved_date=reserved_date,
        reserved_time=reserved_time,
        party_size=party_size,
        operator_note=operator_note.strip(),
        created_by=actor,
    )
    _audit(actor, AuditAction.RESERVATION_CREATED.value, reservation)
    _emit_reservation_event(
        reservation=reservation,
        event_name=EventName.RESERVATION_CREATED.value,
        actor=actor,
    )
    return reservation


@transaction.atomic
def confirm_reservation(*, reservation: Reservation, actor: Account) -> Reservation:
    """Operator approves a requested reservation (REQUESTED → CONFIRMED)."""
    reservation = _lock(reservation)
    if reservation.status != ReservationStatus.REQUESTED.value:
        raise ValueError(f"Cannot confirm a reservation in status '{reservation.status}'.")
    reservation.status = ReservationStatus.CONFIRMED.value
    reservation.save(update_fields=["status", "updated_at"])
    _audit(actor, AuditAction.RESERVATION_CONFIRMED.value, reservation)
    return reservation


@transaction.atomic
def change_reservation(
    *,
    reservation: Reservation,
    actor: Account,
    reserved_date: date | None = None,
    reserved_time: time | None = None,
    party_size: int | None = None,
) -> Reservation:
    """Operator changes the slot of an active reservation.

    Only supplied fields change (``None`` leaves a field as-is); clearing the
    time is not supported in v0. Terminal reservations cannot be changed.
    """
    reservation = _lock(reservation)
    _require_active(reservation, "change")
    fields: list[str] = []
    if reserved_date is not None:
        if reserved_date < timezone.localdate():
            raise ValueError("reserved_date must not be in the past.")
        reservation.reserved_date = reserved_date
        fields.append("reserved_date")
    if reserved_time is not None:
        reservation.reserved_time = reserved_time
        fields.append("reserved_time")
    if party_size is not None:
        if party_size < 1 or party_size > _MAX_PARTY_SIZE:
            raise ValueError(f"party_size must be between 1 and {_MAX_PARTY_SIZE}.")
        reservation.party_size = party_size
        fields.append("party_size")
    if not fields:
        raise ValueError("No reservation fields to change.")
    if (
        Reservation.objects.filter(
            fan=reservation.fan,
            reserved_date=reservation.reserved_date,
            reserved_time=reservation.reserved_time,
            reservation_type=reservation.reservation_type,
            status__in=_ACTIVE_STATUSES,
        )
        .exclude(pk=reservation.pk)
        .exists()
    ):
        raise ValueError("An active reservation for this slot already exists.")
    reservation.save(update_fields=[*fields, "updated_at"])
    _audit(
        actor,
        AuditAction.RESERVATION_CHANGED.value,
        reservation,
        metadata={"changed": fields},
    )
    return reservation


@transaction.atomic
def cancel_reservation(
    *, reservation: Reservation, actor: Account, reason: str = ""
) -> Reservation:
    """Cancel an active reservation (fan or operator) and emit reservation_cancelled.

    Cancellation is terminal; a row is never deleted. Re-cancelling is rejected.
    """
    reservation = _lock(reservation)
    _require_active(reservation, "cancel")
    reservation.status = ReservationStatus.CANCELLED.value
    reservation.cancellation_reason = reason.strip()
    reservation.save(update_fields=["status", "cancellation_reason", "updated_at"])
    _audit(actor, AuditAction.RESERVATION_CANCELLED.value, reservation, reason=reason.strip())
    _emit_reservation_event(
        reservation=reservation,
        event_name=EventName.RESERVATION_CANCELLED.value,
        actor=actor,
    )
    return reservation


@transaction.atomic
def mark_no_show(*, reservation: Reservation, actor: Account, reason: str = "") -> Reservation:
    """Operator records a no-show (terminal). Audit only — no analytics event."""
    reservation = _lock(reservation)
    _require_active(reservation, "mark no-show on")
    reservation.status = ReservationStatus.NO_SHOW.value
    reservation.cancellation_reason = reason.strip()
    reservation.save(update_fields=["status", "cancellation_reason", "updated_at"])
    _audit(actor, AuditAction.RESERVATION_NO_SHOW.value, reservation, reason=reason.strip())
    return reservation


def _lock(reservation: Reservation) -> Reservation:
    """Re-load the row under a row lock so concurrent transitions serialise.

    Without this, two concurrent cancel/no-show/confirm requests could each pass
    the status check on stale state and double-apply (e.g. emit
    ``reservation_cancelled`` twice). ``select_for_update`` serialises them so the
    second sees the committed terminal state and is rejected.
    """
    return Reservation.objects.select_for_update().get(pk=reservation.pk)


def _require_active(reservation: Reservation, verb: str) -> None:
    """Raise unless the reservation is still in an active (non-terminal) state."""
    if reservation.status not in _ACTIVE_STATUSES:
        raise ValueError(f"Cannot {verb} a reservation in status '{reservation.status}'.")


def _audit(
    actor: Account,
    action: str,
    reservation: Reservation,
    *,
    reason: str = "",
    metadata: dict[str, object] | None = None,
) -> None:
    """Write the audit entry for a reservation mutation."""
    entry_metadata: dict[str, object] = {
        # The external UUID (Account.fan_id), matching the analytics event and the
        # other domains' audit rows — not the internal integer PK — so the trail
        # cross-references the event log.
        "fan_id": str(reservation.fan.fan_id),
        "reserved_date": reservation.reserved_date.isoformat(),
        "status": reservation.status,
    }
    if metadata:
        entry_metadata.update(metadata)
    record_audit(
        actor=actor,
        action=action,
        target=str(reservation.id),
        reason=reason,
        metadata=entry_metadata,
    )


def _emit_reservation_event(
    *,
    reservation: Reservation,
    event_name: str,
    actor: Account,
) -> None:
    """Emit a reservation event, deriving actor surface from the actor's role."""
    is_operator = actor.role != Role.FAN.value
    fan_id = str(reservation.fan.fan_id)
    emit_event(
        event_name=event_name,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value if is_operator else ActorType.FAN.value,
        source=EventSource.MANUAL.value if is_operator else EventSource.FAN_APP.value,
        actor_id=str(actor.fan_id),
        fan_id=fan_id,
        actor_is_operator=is_operator,
        ids={"reservation_id": str(reservation.id)},
        context={
            "store_id": reservation.store_id,
            "business_day": reservation.reserved_date.isoformat(),
        },
        payload={
            "fan_id": fan_id,
            "reservation_id": str(reservation.id),
            "reservation_type": reservation.reservation_type,
        },
    )


def _validate_enum(value: str, choices: type[models.TextChoices], field: str) -> None:
    """Raise ``ValueError`` if ``value`` is not a member of ``choices``.

    The rejected value is deliberately not echoed: this validates fan-supplied
    fields (e.g. ``reservation_type``), and reflecting raw input back would leak
    it into the API response (ASS-110 no-echo lesson).
    """
    if value not in choices.values:
        raise ValueError(f"Unknown {field}.")
