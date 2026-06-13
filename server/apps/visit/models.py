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
    """Origin of the visit record.

    ``operator_manual`` is the operator-entered fallback (ASS-94); ``qr_self`` is
    a fan self-check-in via a server-issued rotating QR (ASS-99) that an operator
    scanned. Both are genuine fan visits (they count toward MSFC); the source
    only records *how* the check-in was captured.
    """

    OPERATOR_MANUAL = "operator_manual", "operator_manual"
    QR_SELF = "qr_self", "qr_self"


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


class CheckinToken(models.Model):
    """A short-lived, single-use rotating check-in credential (ASS-99).

    CONSTRAINTS #18 forbids a *static* QR — a screenshot would be replayable and
    shareable. The fan app displays this token as a QR for a short window
    (``_DEFAULT_TTL``, the 15~60s rotation band); the server issues a fresh token
    on each refresh and accepts any token at most once, so a leaked screenshot is
    useless the moment it expires or is redeemed. Redemption (an operator scan)
    records a real fan visit through the visit domain — the fan is the analytics
    actor, the operator is provenance.

    The row is kept after redemption (not deleted) so a scan is auditable and a
    replay attempt resolves to "already redeemed" rather than "unknown token".
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fan = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="checkin_tokens",
    )
    # High-entropy opaque value (secrets.token_urlsafe); unique so a scan resolves
    # to exactly one credential. It is a bearer secret for its short lifetime.
    token = models.CharField(max_length=64, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    redeemed_at = models.DateTimeField(null=True, blank=True)
    redeemed_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="redeemed_checkin_tokens",
    )
    visit = models.ForeignKey(
        "visit.VisitRecord",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="checkin_token",
    )

    class Meta:
        indexes = [
            models.Index(fields=["fan", "issued_at"]),
            models.Index(fields=["expires_at"]),
        ]
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        """Identify the token by fan and lifecycle for admin/log display."""
        state = "redeemed" if self.redeemed_at else "pending"
        return f"checkin_token:{self.id}:{self.fan_id}:{state}"
