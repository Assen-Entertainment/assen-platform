"""Tests for the reservation/waitlist service (F03, ASS-109 v0).

Covers create (fan + operator-on-behalf), the create guards (non-fan subject,
blocked fan, past date, party-size bounds, duplicate active slot), the
approve/change/cancel/no-show lifecycle, and the canonical
``reservation_created`` / ``reservation_cancelled`` emission. External-store sync
and prepaid/seat assignment are out of v0 and not exercised here.
"""

from __future__ import annotations

from datetime import date, time, timedelta

import pytest
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEntry
from apps.event_log.events import ActorType, EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account, Role
from apps.reservation.models import Reservation, ReservationStatus, ReservationType
from apps.reservation.services import (
    cancel_reservation,
    change_reservation,
    confirm_reservation,
    create_reservation,
    mark_no_show,
)
from apps.safety.models import BlockScope, UserBlock

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _fan() -> Account:
    """Create a fan account (the reservation subject)."""
    return _account(Role.FAN.value)


def _operator() -> Account:
    """Create an operator account (the actor)."""
    return _account(Role.OPERATOR.value)


def _tomorrow() -> date:
    """A safely-future reserved date (today passes the past-date guard too)."""
    return timezone.localdate() + timedelta(days=1)


def _block(fan: Account, actor: Account, scope: str) -> UserBlock:
    """Place an active hard block on a fan."""
    return UserBlock.objects.create(
        target=fan,
        block_scope=scope,
        block_reason="policy_violation",
        effective_from=timezone.now(),
        created_by=actor,
    )


def test_fan_create_emits_reservation_created() -> None:
    """A fan registers a reservation: row is REQUESTED, event + audit are written."""
    fan = _fan()
    reservation = create_reservation(
        fan=fan,
        actor=fan,
        reserved_date=_tomorrow(),
        reserved_time=time(14, 0),
        party_size=2,
    )

    assert reservation.status == ReservationStatus.REQUESTED.value
    assert reservation.reservation_type == ReservationType.RESERVATION.value
    assert reservation.created_by_id == fan.id

    event = EventRecord.objects.get(event_name=EventName.RESERVATION_CREATED.value)
    assert event.payload["fan_id"] == str(fan.fan_id)
    assert event.payload["reservation_id"] == str(reservation.id)
    assert event.payload["reservation_type"] == "reservation"
    assert event.ids["reservation_id"] == str(reservation.id)
    assert event.actor_type == ActorType.FAN.value
    assert event.actor_is_operator is False
    assert AuditEntry.objects.filter(
        action=AuditAction.RESERVATION_CREATED.value, target=str(reservation.id)
    ).exists()


def test_operator_create_on_behalf_is_operator_attributed() -> None:
    """An operator records a reservation for a fan; the event is operator-attributed."""
    fan = _fan()
    operator = _operator()
    reservation = create_reservation(
        fan=fan,
        actor=operator,
        reserved_date=_tomorrow(),
        operator_note="phone booking",
    )

    assert reservation.created_by_id == operator.id
    assert reservation.operator_note == "phone booking"
    event = EventRecord.objects.get(event_name=EventName.RESERVATION_CREATED.value)
    assert event.actor_type == ActorType.OPERATOR.value
    assert event.actor_is_operator is True
    assert event.payload["fan_id"] == str(fan.fan_id)


def test_blocked_fan_cannot_reserve() -> None:
    """A fan with an active reservation block is refused (ASS-111 enforcement)."""
    fan = _fan()
    _block(fan, _operator(), BlockScope.RESERVATION.value)
    with pytest.raises(ValueError, match="blocked"):
        create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow())
    assert not Reservation.objects.exists()


def test_all_scope_block_also_refuses_reservation() -> None:
    """A catch-all (``all``) block also covers the reservation surface."""
    fan = _fan()
    _block(fan, _operator(), BlockScope.ALL.value)
    with pytest.raises(ValueError, match="blocked"):
        create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow())


def test_non_fan_subject_rejected() -> None:
    """A reservation can only be recorded for a fan account."""
    operator = _operator()
    with pytest.raises(ValueError, match="fan accounts"):
        create_reservation(fan=operator, actor=operator, reserved_date=_tomorrow())


def test_past_date_rejected() -> None:
    """A reserved date in the past is rejected."""
    fan = _fan()
    with pytest.raises(ValueError, match="past"):
        create_reservation(
            fan=fan, actor=fan, reserved_date=timezone.localdate() - timedelta(days=1)
        )


def test_party_size_bounds_rejected() -> None:
    """Party size must be within 1..max."""
    fan = _fan()
    with pytest.raises(ValueError, match="party_size"):
        create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow(), party_size=0)
    with pytest.raises(ValueError, match="party_size"):
        create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow(), party_size=999)


def test_unknown_reservation_type_rejected() -> None:
    """An out-of-domain reservation_type is rejected."""
    fan = _fan()
    with pytest.raises(ValueError, match="reservation_type"):
        create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow(), reservation_type="party")


def test_duplicate_active_slot_rejected() -> None:
    """An identical active slot for the same fan is a double-submit and refused."""
    fan = _fan()
    day = _tomorrow()
    create_reservation(fan=fan, actor=fan, reserved_date=day, reserved_time=time(15, 0))
    with pytest.raises(ValueError, match="already exists"):
        create_reservation(fan=fan, actor=fan, reserved_date=day, reserved_time=time(15, 0))


def test_duplicate_slot_allowed_after_cancel() -> None:
    """Re-booking the same slot is fine once the prior reservation is cancelled."""
    fan = _fan()
    day = _tomorrow()
    first = create_reservation(fan=fan, actor=fan, reserved_date=day, reserved_time=time(16, 0))
    cancel_reservation(reservation=first, actor=fan)
    again = create_reservation(fan=fan, actor=fan, reserved_date=day, reserved_time=time(16, 0))
    assert again.status == ReservationStatus.REQUESTED.value


def test_confirm_transitions_and_audits() -> None:
    """An operator confirms a requested reservation; a second confirm is rejected."""
    fan = _fan()
    operator = _operator()
    reservation = create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow())
    confirmed = confirm_reservation(reservation=reservation, actor=operator)
    assert confirmed.status == ReservationStatus.CONFIRMED.value
    assert AuditEntry.objects.filter(
        action=AuditAction.RESERVATION_CONFIRMED.value, target=str(reservation.id)
    ).exists()
    with pytest.raises(ValueError, match="confirm"):
        confirm_reservation(reservation=confirmed, actor=operator)


def test_change_updates_fields_and_audits() -> None:
    """Changing an active reservation updates only supplied fields and audits them."""
    fan = _fan()
    operator = _operator()
    reservation = create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow(), party_size=2)
    changed = change_reservation(reservation=reservation, actor=operator, party_size=4)
    assert changed.party_size == 4
    entry = AuditEntry.objects.get(
        action=AuditAction.RESERVATION_CHANGED.value, target=str(reservation.id)
    )
    assert entry.metadata["changed"] == ["party_size"]


def test_change_terminal_rejected() -> None:
    """A cancelled reservation cannot be changed."""
    fan = _fan()
    reservation = create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow())
    cancel_reservation(reservation=reservation, actor=fan)
    with pytest.raises(ValueError, match="change"):
        change_reservation(reservation=reservation, actor=_operator(), party_size=3)


def test_cancel_emits_reservation_cancelled() -> None:
    """Cancelling emits the canonical reservation_cancelled and audits it."""
    fan = _fan()
    operator = _operator()
    reservation = create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow())
    confirm_reservation(reservation=reservation, actor=operator)
    cancelled = cancel_reservation(reservation=reservation, actor=operator, reason="store closed")
    assert cancelled.status == ReservationStatus.CANCELLED.value
    assert cancelled.cancellation_reason == "store closed"
    event = EventRecord.objects.get(event_name=EventName.RESERVATION_CANCELLED.value)
    assert event.payload["reservation_id"] == str(reservation.id)
    assert event.actor_is_operator is True
    assert AuditEntry.objects.filter(
        action=AuditAction.RESERVATION_CANCELLED.value, target=str(reservation.id)
    ).exists()


def test_cancel_terminal_rejected() -> None:
    """Re-cancelling a cancelled reservation is rejected."""
    fan = _fan()
    reservation = create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow())
    cancel_reservation(reservation=reservation, actor=fan)
    with pytest.raises(ValueError, match="cancel"):
        cancel_reservation(reservation=reservation, actor=fan)


def test_no_show_audits_without_event() -> None:
    """A no-show is a terminal status with an audit entry but no analytics event."""
    fan = _fan()
    operator = _operator()
    reservation = create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow())
    confirm_reservation(reservation=reservation, actor=operator)
    no_show = mark_no_show(reservation=reservation, actor=operator, reason="did not arrive")
    assert no_show.status == ReservationStatus.NO_SHOW.value
    assert AuditEntry.objects.filter(
        action=AuditAction.RESERVATION_NO_SHOW.value, target=str(reservation.id)
    ).exists()
    # No reservation event maps to a no-show.
    assert not EventRecord.objects.filter(event_name=EventName.RESERVATION_CANCELLED.value).exists()


def test_waitlist_type_is_stored() -> None:
    """A waitlist entry is recorded with its type."""
    fan = _fan()
    reservation = create_reservation(
        fan=fan,
        actor=fan,
        reserved_date=_tomorrow(),
        reservation_type=ReservationType.WAITLIST.value,
    )
    assert reservation.reservation_type == ReservationType.WAITLIST.value


def test_audit_metadata_records_fan_uuid() -> None:
    """The audit trail stores the external fan UUID, matching the event log."""
    fan = _fan()
    reservation = create_reservation(fan=fan, actor=fan, reserved_date=_tomorrow())
    entry = AuditEntry.objects.get(
        action=AuditAction.RESERVATION_CREATED.value, target=str(reservation.id)
    )
    assert entry.metadata["fan_id"] == str(fan.fan_id)


def test_change_onto_existing_active_slot_rejected() -> None:
    """Changing a reservation onto another active slot the fan holds is refused."""
    fan = _fan()
    operator = _operator()
    day = _tomorrow()
    create_reservation(fan=fan, actor=fan, reserved_date=day, reserved_time=time(11, 0))
    movable = create_reservation(fan=fan, actor=fan, reserved_date=day, reserved_time=time(12, 0))
    with pytest.raises(ValueError, match="already exists"):
        change_reservation(reservation=movable, actor=operator, reserved_time=time(11, 0))
