"""Domain models for coupons + points (F09, ASS-108 v0).

A retention ledger: operators issue coupons (revisit / event / manual / apology),
fans redeem them, and operators can cancel or expire them; a separate point
ledger records integer point deltas. Every mutation emits the canonical
``coupon_*`` / ``point_*`` event from the service so analytics can measure
post-coupon revisit conversion.

Out of scope for v0 (held — the issue Blocker): the **coupon value / discount
rate**. 쿠폰 가치/할인율은 승인 필요 — the model stores **no discount/money
figure** (``discount_amount`` is *conditional* in Data_Event_Schema, so a coupon
carries only its ``coupon_type``; the approved discount value is a separate,
approval-gated deferred slice). Points are an integer count with no monetary
value or auto-earn rule in v0 (operators grant explicitly).
"""

from __future__ import annotations

import uuid

from django.db import models

# Single café for Release 0.1 (mirrors visit.models.DEFAULT_STORE_ID rationale).
DEFAULT_STORE_ID = "hatsukoi"


class CouponType(models.TextChoices):
    """Coupon category (Data_Event_Schema coupon_redeemed ``coupon_type`` domain)."""

    REVISIT = "revisit", "revisit"
    EVENT = "event", "event"
    MANUAL = "manual", "manual"
    APOLOGY = "apology", "apology"


class CouponStatus(models.TextChoices):
    """Coupon lifecycle. Active is usable; the rest are terminal."""

    ACTIVE = "active", "active"
    REDEEMED = "redeemed", "redeemed"
    CANCELLED = "cancelled", "cancelled"
    EXPIRED = "expired", "expired"


class Coupon(models.Model):
    """A single coupon granted to a fan (F09).

    Carries only ``coupon_type`` — no discount/money figure is stored (the value
    is the approval-gated, deferred slice). ``redemption_id`` is the stable
    ``coupon_redemption_id`` minted on redeem (used for POS discount reconciliation
    in F13, wired later).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fan = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="coupons",
    )
    coupon_type = models.CharField(max_length=16, choices=CouponType.choices)
    status = models.CharField(
        max_length=16, choices=CouponStatus.choices, default=CouponStatus.ACTIVE
    )
    # The coupon_redemption_id minted on redeem (null until then). For F13 POS
    # discount reconciliation; unique when present so a redemption id is stable.
    redemption_id = models.UUIDField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)
    store_id = models.CharField(max_length=64, default=DEFAULT_STORE_ID)
    issued_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="issued_coupons",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # A minted redemption id is unique (stable POS-reconciliation key).
            models.UniqueConstraint(
                fields=["redemption_id"],
                condition=models.Q(redemption_id__isnull=False),
                name="uniq_coupon_redemption_id",
            ),
        ]
        indexes = [
            models.Index(fields=["fan", "status"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Summarise the coupon for log/admin display (no personal data)."""
        return f"coupon {self.id} {self.coupon_type} ({self.status})"


class PointEntry(models.Model):
    """One point-ledger movement for a fan (F09, P0_optional).

    The balance is the sum of a fan's ``delta`` rows (append-only ledger). v0 has
    no monetary value and no auto-earn rule — operators grant/adjust explicitly.
    ``reason`` is an operator-authored operational note (no fan PII).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fan = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="point_entries",
    )
    delta = models.IntegerField()
    # Operator-authored operational note (no fan PII; never returned to the fan).
    reason = models.CharField(max_length=200, blank=True, default="")
    # Optional caller-supplied idempotency key: a retry with the same (fan,
    # reference) returns the existing entry instead of double-posting. Empty =
    # unreferenced (not deduped).
    reference = models.CharField(max_length=100, blank=True, default="")
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_point_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Idempotency backstop: one entry per (fan, non-empty reference).
            models.UniqueConstraint(
                fields=["fan", "reference"],
                condition=~models.Q(reference=""),
                name="uniq_point_entry_reference",
            ),
        ]
        indexes = [
            models.Index(fields=["fan", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Summarise the point entry for log/admin display."""
        return f"point {self.id} fan={self.fan_id} delta={self.delta}"
