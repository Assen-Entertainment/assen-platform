"""Domain models for reservation/waitlist (F03, ASS-109 v0).

A reservation is an independent operational ledger row: a fan registers a
date/time/party-size reservation or a waitlist entry (from the app), and
operators approve / change / cancel / mark-no-show it. The append-only
analytics signal is ``reservation_created`` / ``reservation_cancelled``
(emitted from the service); the row itself carries the operational lifecycle.

Out of scope for v0 (held): prepaid reservations, complex seat assignment, and
external-store / 네이버 예약 sync (the operational form is a PRD open question /
P0-excluded "외부 매장 예약"). Those land as separate slices once decided.
"""

from __future__ import annotations

import uuid

from django.db import models

# Single café for Release 0.1 (mirrors visit.models.DEFAULT_STORE_ID rationale).
DEFAULT_STORE_ID = "hatsukoi"


class ReservationType(models.TextChoices):
    """예약 (a held date/time slot) vs 대기 (waitlist when full)."""

    RESERVATION = "reservation", "reservation"
    WAITLIST = "waitlist", "waitlist"


class ReservationStatus(models.TextChoices):
    """Reservation lifecycle. Cancelled/no-show are terminal; rows are never deleted."""

    REQUESTED = "requested", "requested"
    CONFIRMED = "confirmed", "confirmed"
    CANCELLED = "cancelled", "cancelled"
    NO_SHOW = "no_show", "no_show"


class Reservation(models.Model):
    """A fan's reservation or waitlist entry for a store visit (F03).

    ``fan`` is the subject; ``created_by`` is whoever recorded it (the fan from
    the app, or an operator acting on the fan's behalf). Blocked fans are
    refused at the service boundary (``BlockScope.RESERVATION`` — the enforcement
    surface ASS-111 deferred to F03). ``operator_note`` is operator-only; no fan
    free-text is stored, so a fan cannot push PII into the operational trail.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fan = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    store_id = models.CharField(max_length=64, default=DEFAULT_STORE_ID)
    reservation_type = models.CharField(
        max_length=16,
        choices=ReservationType.choices,
        default=ReservationType.RESERVATION,
    )
    status = models.CharField(
        max_length=16,
        choices=ReservationStatus.choices,
        default=ReservationStatus.REQUESTED,
    )
    reserved_date = models.DateField()
    # Waitlist entries may be time-flexible, so the slot time is optional.
    reserved_time = models.TimeField(null=True, blank=True)
    party_size = models.PositiveSmallIntegerField(default=1)
    operator_note = models.TextField(blank=True, default="")
    # Operational trail for a cancel or a no-show; carries no personal data.
    cancellation_reason = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_reservations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Race-safe backstop for create_reservation's double-submit guard: one
            # active (requested/confirmed) reservation per fan + slot + type. Two
            # partial uniques are needed because SQL treats each NULL reserved_time
            # as distinct — the time-set and the time-omitted (date-only / flexible
            # waitlist) cases must each be de-duped to close the concurrency window.
            models.UniqueConstraint(
                fields=["fan", "reserved_date", "reserved_time", "reservation_type"],
                condition=models.Q(status__in=["requested", "confirmed"]),
                name="uniq_active_reservation_slot",
            ),
            models.UniqueConstraint(
                fields=["fan", "reserved_date", "reservation_type"],
                condition=models.Q(
                    status__in=["requested", "confirmed"], reserved_time__isnull=True
                ),
                name="uniq_active_reservation_slot_no_time",
            ),
        ]
        indexes = [
            models.Index(fields=["reserved_date"]),
            models.Index(fields=["fan", "-created_at"]),
            models.Index(fields=["status", "reserved_date"]),
            models.Index(fields=["store_id", "reserved_date"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Summarise the reservation for log/admin display (no personal data)."""
        return f"{self.reservation_type} {self.id} ({self.status})"
