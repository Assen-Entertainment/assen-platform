"""Domain models for operator-managed cast schedules (ASS-93, F05).

Date-keyed cast work schedules. Operators create/edit/unpublish entries, but a
change to a *published* entry is not applied directly — it is filed as a
:class:`ScheduleChangeRequest` and only takes effect after a *different* staff
member approves it (separation of duties), leaving a change log. This addresses
the PRD risk of schedule churn confusing fans/reservation-holders.

The fan-facing ``schedule_viewed`` analytics event lives on the fan read path;
operator management here is operational (audited), not an analytics event.
``cast_id`` is a plain identifier — the cast app is a P0 placeholder with no
model yet (swap to a FK when it lands).
"""

from __future__ import annotations

import uuid

from django.db import models


class ScheduleStatus(models.TextChoices):
    """Publication lifecycle for a schedule entry (비공개 = unpublished)."""

    DRAFT = "draft", "draft"
    PUBLISHED = "published", "published"
    UNPUBLISHED = "unpublished", "unpublished"


class ScheduleEntry(models.Model):
    """One cast's work window on a given date.

    Never deleted — unpublished hides it from fans while preserving history and
    the reservation/notice trail.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_date = models.DateField()
    cast_id = models.CharField(max_length=64)
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=16,
        choices=ScheduleStatus.choices,
        default=ScheduleStatus.DRAFT,
    )
    note = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_schedule_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["work_date", "status"]),
            models.Index(fields=["cast_id", "work_date"]),
        ]
        ordering = ["work_date", "start_time"]

    def __str__(self) -> str:
        """Identify the entry by date/cast/status."""
        return f"schedule:{self.id}:{self.cast_id}@{self.work_date}/{self.status}"


class ChangeRequestStatus(models.TextChoices):
    """Lifecycle of a proposed change to a published entry."""

    PENDING = "pending", "pending"
    APPROVED = "approved", "approved"
    REJECTED = "rejected", "rejected"


class ScheduleChangeRequest(models.Model):
    """A proposed change to a published :class:`ScheduleEntry`, pending approval.

    Holds the proposed field values (``proposed``) until a *different* staff
    member approves (then they are applied to the entry) or rejects. This row is
    itself the change log: who requested/decided, when, and the before/after.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(
        ScheduleEntry,
        on_delete=models.PROTECT,
        related_name="change_requests",
    )
    # Proposed field overrides (work_date/start_time/end_time/note as strings).
    proposed = models.JSONField(default=dict)
    # Snapshot of the entry before the change, for the audit/before-after view.
    before = models.JSONField(default=dict)
    reason = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=ChangeRequestStatus.choices,
        default=ChangeRequestStatus.PENDING,
    )
    requested_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="requested_schedule_changes",
    )
    decided_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="decided_schedule_changes",
        null=True,
        blank=True,
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["entry", "status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the change request by entry and status."""
        return f"sched-change:{self.id}:{self.entry_id}/{self.status}"
