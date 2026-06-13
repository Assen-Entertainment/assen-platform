"""Domain models for operator-managed visit records."""

from __future__ import annotations

import uuid

from django.db import models

# Release 0.1 serves a single café (하츠코이), and the operator→store mapping is
# not modelled yet, so visit records default to this store id. It is denormalised
# onto the record (not derived at emit time) because POS reconciliation and the
# canonical ``visit_checked_in`` event both require a stable ``store_id`` per
# visit; multi-store lands when operators carry a store association.
DEFAULT_STORE_ID = "hatsukoi"


class VisitRecordStatus(models.TextChoices):
    """Lifecycle for a visit record that is never physically deleted."""

    ACTIVE = "active", "active"
    VOIDED = "voided", "voided"


class VisitRecordSource(models.TextChoices):
    """Origin of the visit record; QR lands in ASS-99."""

    OPERATOR_MANUAL = "operator_manual", "operator_manual"


class VisitRecord(models.Model):
    """Operator-maintained fan visit history for F07, MSFC, and POS checks.

    This is the source record for manual offline check-ins. It is append-oriented
    in practice: rows are not deleted when wrong, only corrected or voided, so
    audit review and POS reconciliation can see the operational trail.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fan = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="visit_records",
    )
    visited_at = models.DateTimeField()
    store_id = models.CharField(max_length=64, default=DEFAULT_STORE_ID)
    status = models.CharField(
        max_length=16,
        choices=VisitRecordStatus.choices,
        default=VisitRecordStatus.ACTIVE,
    )
    source = models.CharField(
        max_length=32,
        choices=VisitRecordSource.choices,
        default=VisitRecordSource.OPERATOR_MANUAL,
    )
    note = models.TextField(blank=True, default="")
    void_reason = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_visit_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["visited_at"]),
            models.Index(fields=["fan", "visited_at"]),
            models.Index(fields=["status", "visited_at"]),
        ]
        ordering = ["-visited_at", "-created_at"]

    def __str__(self) -> str:
        """Identify the visit by fan and visited time for admin/log display."""
        return f"visit:{self.id}:{self.fan_id}@{self.visited_at.isoformat()}"
