"""Domain models for event campaigns (F10, ASS-107 v0).

An event campaign is an operator-authored announcement for a high-engagement
visit (birthday / guest day / theme day, …). Operators create it as a draft,
publish it (the fail-closed "승인 전 비공개" gate), and close it; fans view
published campaigns and reserve / waitlist a slot.

The append-only analytics signals are ``event_viewed`` (impression),
``event_reserved`` (reserve/waitlist), and ``event_reservation_cancelled``
(correction) — emitted from the service.

Out of scope for v0 (held): the **price / participation-fee values** (issue:
"이벤트 가격·참여 방식 값은 승인 필요 — 승인 전 비공개" — a pricing decision,
CONSTRAINTS L91; the platform stores no money figure here and gates publication
instead), plus seat-assigned ticketing, prepaid tickets, and external sales
(PRD F10 P0 제외).
"""

from __future__ import annotations

import uuid

from django.db import models

# Single café for Release 0.1 (mirrors visit.models.DEFAULT_STORE_ID rationale).
DEFAULT_STORE_ID = "hatsukoi"


class EventType(models.TextChoices):
    """Event category (Data_Event_Schema event_reserved ``event_type`` domain)."""

    BIRTHDAY = "birthday", "birthday"
    THEME_DAY = "theme_day", "theme_day"
    GUEST_DAY = "guest_day", "guest_day"
    COSTUME_DAY = "costume_day", "costume_day"
    OTHER = "other", "other"


class CampaignStatus(models.TextChoices):
    """Lifecycle. Draft is fan-invisible (승인 전 비공개); closed is terminal."""

    DRAFT = "draft", "draft"
    PUBLISHED = "published", "published"
    CLOSED = "closed", "closed"


class EventReservationStatus(models.TextChoices):
    """A fan's hold on a campaign (Data_Event_Schema ``reservation_status``)."""

    RESERVED = "reserved", "reserved"
    WAITLISTED = "waitlisted", "waitlisted"
    CANCELLED = "cancelled", "cancelled"


class EventCampaign(models.Model):
    """An operator-authored event announcement (F10).

    Fan-visible only while ``status=published`` — a draft is the fail-closed
    "승인 전 비공개" state, so price/participation values that still need approval
    never reach fans before an operator publishes. No money figure is stored in
    v0 (the price value is the approval-gated, deferred slice).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    event_type = models.CharField(max_length=16, choices=EventType.choices, default=EventType.OTHER)
    # Optional headlining cast; campaigns can be store-wide with no single cast.
    cast = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="event_campaigns",
        null=True,
        blank=True,
    )
    store_id = models.CharField(max_length=64, default=DEFAULT_STORE_ID)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    # Operator-authored precautions (주의사항); operational text, no fan PII.
    notice = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT
    )
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_event_campaigns",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "starts_at"]),
            models.Index(fields=["store_id", "starts_at"]),
            models.Index(fields=["event_type"]),
        ]
        ordering = ["-starts_at", "-created_at"]

    def __str__(self) -> str:
        """Summarise the campaign for log/admin display (no personal data)."""
        return f"{self.event_type} {self.id} ({self.status})"


class EventReservation(models.Model):
    """A fan's reservation or waitlist hold on a published event campaign (F10)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        EventCampaign,
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    fan = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="event_reservations",
    )
    status = models.CharField(
        max_length=16,
        choices=EventReservationStatus.choices,
        default=EventReservationStatus.RESERVED,
    )
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_event_reservations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # One active (reserved/waitlisted) hold per fan per campaign; the
            # race-safe backstop for the service double-submit guard. A cancelled
            # row frees the fan to re-reserve.
            models.UniqueConstraint(
                fields=["campaign", "fan"],
                condition=models.Q(status__in=["reserved", "waitlisted"]),
                name="uniq_active_event_reservation",
            ),
        ]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["fan", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Summarise the event reservation for log/admin display."""
        return f"event-reservation {self.id} ({self.status})"
