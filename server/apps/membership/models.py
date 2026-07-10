"""Membership models — MembershipTier catalog + mock Subscription (SDLC 09 §3).

The *tier catalog* (``MembershipTier``) carries name, price (display KRW/period),
benefits, and presentation flags. B4 adds a **mock** ``Subscription``: subscribing
records an active membership but **no real payment is taken and no money moves** —
recurring billing / PG / settlement are gated (B7). ``next_billing_date`` is a
display value, not a settlement schedule.

Migrated app — ``migrate`` applies ``0001_initial``; regenerate with
``makemigrations`` when models change.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.db import models


class MembershipTier(models.Model):
    """A creator's membership tier (maps to the frontend ``MembershipTier``)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
        "creator.Creator",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="tiers",
    )
    name = models.CharField(max_length=40)
    # Display price in whole KRW per period. Not a billing/settlement figure.
    price = models.PositiveIntegerField(default=0)
    period = models.CharField(max_length=8, default="월")
    # List of benefit strings (frontend ``benefits: string[]``).
    benefits = models.JSONField(default=list)
    badge = models.CharField(max_length=20, blank=True, default="")
    featured = models.BooleanField(default=False)
    # Studio toggle (R3): an inactive tier is hidden from the public catalog but kept
    # for the owner to re-activate (soft archive), so existing subscriptions survive.
    active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["creator", "sort_order"]),
        ]
        ordering = ["sort_order", "price"]

    def __str__(self) -> str:
        """Identify the tier."""
        return f"tier:{self.name}"


class SubscriptionStatus(models.TextChoices):
    """Subscription states surfaced to the fan."""

    ACTIVE = "active", "active"
    CANCELLED = "cancelled", "cancelled"


class Subscription(models.Model):
    """A fan's mock membership subscription. MOCK: no money moves (B7 gated).

    End-of-period cancellation ("해지 예정"): :meth:`cancel <apps.membership.api>`
    records ``cancelled_at`` but keeps ``status = active`` so the membership stays
    usable until the period ends; a real billing job (post-mock) would flip it to
    ``cancelled`` at ``next_billing_date``. The API exposes a derived
    ``cancel_scheduled`` flag so the web renders "해지 예정".
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fan = models.ForeignKey(
        "identity.Account", on_delete=models.CASCADE, related_name="subscriptions"
    )
    tier = models.ForeignKey(
        "membership.MembershipTier",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    # Denormalised owning creator (B2): copied from ``tier.creator`` at write time so
    # the "one active subscription per creator" rule can be a DB constraint (the
    # rule is per-creator, but a fan subscribes to a *tier*). Fixed on first save;
    # nullable because a tier may be creatorless (global), in which case NULLs stay
    # distinct and the per-creator constraint does not apply.
    creator = models.ForeignKey(
        "creator.Creator",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="fan_subscriptions",
    )
    status = models.CharField(
        max_length=16, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE
    )
    started_at = models.DateTimeField(auto_now_add=True)
    # Mock billing anchor (display only; no PG/settlement — B7 gated).
    next_billing_date = models.DateField()
    # Set when the fan schedules end-of-period cancellation; status stays active.
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["fan", "-started_at"]),
        ]
        ordering = ["-started_at"]
        constraints = [
            # At most one ACTIVE subscription per (fan, creator). Partial on active
            # status so a cancelled subscription does not block re-subscribing.
            # Materialised by the app's migration (applied by ``migrate``).
            models.UniqueConstraint(
                fields=["fan", "creator"],
                condition=models.Q(status="active"),
                name="uniq_active_subscription_per_creator",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Pin ``creator`` from the tier on first write (B2 denormalisation)."""
        if self.creator_id is None and self.tier_id is not None:
            self.creator_id = self.tier.creator_id
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Identify the subscription edge and its state."""
        return f"sub:{self.fan_id}->{self.tier_id}:{self.status}"
