"""Membership catalog model — MembershipTier (SDLC 09 §3, E11/B1).

Only the *tier catalog* lands in B1/B2: name, price (display KRW/period),
benefits, and presentation flags. Subscriptions and recurring billing are
**gated** (B4/B7, 대표·법무·PG) and absent here — nothing that decides money.

Migration-less app (``migrate --run-syncdb``); do not add a migrations package.
"""

from __future__ import annotations

import uuid

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
