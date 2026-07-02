"""Append-only event log: the canonical analytics record store.

``EventRecord`` is immutable by construction (CONSTRAINTS: append-only event_log,
ADR-0001). Once written, a row is never updated or deleted in normal operation:
corrections are expressed as *new* events (e.g. ``visit_invalidated``), never as
mutations of the original. This is enforced in code here, and proven by tests,
because analytics correctness depends on the log being an immutable ledger.

Mirrors Data_Event_Schema.md: the full event envelope (ids/context/properties/
quality) is preserved in JSON columns, while a handful of fields are denormalised
into indexed columns so MSFC and the 30-day revisit query run as plain SQL.
"""

from __future__ import annotations

import uuid
from typing import Any, NoReturn

from django.db import models

from apps.event_log.events import (
    ActorType,
    EventName,
    EventSource,
    EventStatus,
)


class AppendOnlyViolation(Exception):
    """Raised when code attempts to mutate or delete a persisted event.

    Surfaces the append-only invariant as a hard failure rather than letting a
    silent update corrupt the ledger.
    """


class EventRecordManager(models.Manager["EventRecord"]):
    """Manager that refuses bulk mutation/deletion of the event ledger.

    Django's ``QuerySet.update``/``delete`` bypass ``Model.save``/``delete``, so
    blocking only the model methods would leave a hole. Overriding the manager's
    queryset closes it: ``EventRecord.objects.filter(...).delete()`` is rejected
    too. Reads are unaffected.
    """

    def get_queryset(self) -> EventRecordQuerySet:
        """Return the append-only queryset so writes through it are blocked."""
        return EventRecordQuerySet(self.model, using=self._db)


class EventRecordQuerySet(models.QuerySet["EventRecord"]):
    """QuerySet that blocks the mutation paths that bypass ``Model.save``."""

    def update(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Reject bulk updates — events are immutable once written."""
        raise AppendOnlyViolation(
            "EventRecord is append-only; bulk update is not permitted. "
            "Record a corrective event instead."
        )

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Reject bulk deletes — events are immutable once written."""
        raise AppendOnlyViolation(
            "EventRecord is append-only; bulk delete is not permitted."
        )


class EventRecord(models.Model):
    """One recorded, immutable platform event.

    Use :func:`apps.event_log.services.emit_event` to create rows; it validates
    the payload against the registry. Direct ``save`` of a *new* row is allowed
    (that is how emission persists), but re-saving an existing row or deleting
    any row raises :class:`AppendOnlyViolation`.
    """

    objects = EventRecordManager()

    # --- Identity ----------------------------------------------------------
    event_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    event_name = models.CharField(max_length=64, choices=EventName.choices)
    schema_version = models.CharField(max_length=16, default="1.0")

    # --- Timing ------------------------------------------------------------
    # occurred_at = real-world action time; received_at = ingest time. They
    # differ for backfilled/imported events, so both are first-class.
    occurred_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)

    # --- Actor / source ----------------------------------------------------
    actor_type = models.CharField(max_length=16, choices=ActorType.choices)
    actor_id = models.CharField(max_length=64, blank=True, default="")
    source = models.CharField(max_length=16, choices=EventSource.choices)
    source_system = models.CharField(max_length=32, default="assen_platform")

    # --- Denormalised index columns ---------------------------------------
    # Duplicated out of the ``ids`` envelope purely so the MSFC / 30-day revisit
    # SQL can filter and join without JSON extraction. ``fan_id`` empty (not the
    # actor) is the convention for "operator/system activity excluded from fan
    # metrics", complementing ``actor_is_operator``.
    fan_id = models.CharField(max_length=64, blank=True, default="")
    cast_id = models.CharField(max_length=64, blank=True, default="")
    visit_id = models.CharField(max_length=64, blank=True, default="")

    status = models.CharField(
        max_length=16,
        choices=EventStatus.choices,
        default=EventStatus.COMPLETED,
    )

    # --- Quality flags (subset of Data_Event_Schema ``quality`` object) ----
    # ``actor_is_operator`` lets MSFC and revisit queries exclude operator test
    # traffic without inspecting actor_type, per the operator-exclusion rule.
    actor_is_operator = models.BooleanField(default=False)
    is_invalidated = models.BooleanField(default=False)
    invalid_reason = models.CharField(max_length=255, blank=True, default="")

    # --- Full envelope -----------------------------------------------------
    ids = models.JSONField(default=dict, blank=True)
    context = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    quality = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            # Primary analytics access path: an event type over a time window.
            models.Index(fields=["event_name", "occurred_at"]),
            # Per-fan history: MSFC start, 30-day revisit self-join, fan timeline.
            models.Index(fields=["fan_id"]),
        ]
        ordering = ["-occurred_at"]

    def __str__(self) -> str:
        """Human-readable identity for admin/log output."""
        return f"{self.event_name}@{self.occurred_at.isoformat()} ({self.event_id})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Allow first insert; reject any re-save of an existing row.

        ``self._state.adding`` is True only for the initial insert. A second
        ``save`` (an update) means someone is mutating the ledger, which the
        append-only contract forbids.
        """
        if not self._state.adding:
            raise AppendOnlyViolation(
                f"EventRecord {self.pk} is append-only and cannot be modified. "
                "Record a corrective event instead."
            )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Reject row deletion — the ledger never forgets."""
        raise AppendOnlyViolation(
            f"EventRecord {self.pk} is append-only and cannot be deleted."
        )
