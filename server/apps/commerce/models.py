"""Commerce catalog model — Product (SDLC 09 §3 — commerce context, E11/B1).

Only the *catalog* lands in B1/B2: a ``Product`` is a display listing with a
catalog ``price`` (integer KRW, a display value — NOT a settlement figure).
Orders, payment, and settlement are **gated** (B7, 대표·법무·PG) and are
deliberately absent here — this app stores nothing that decides money owed.

Migration-less app (``migrate --run-syncdb``); do not add a migrations package.
"""

from __future__ import annotations

import uuid

from django.db import models


class ProductType(models.TextChoices):
    """Monetizable item kinds (mirror the frontend ``MonetizableItemType``)."""

    GOODS = "goods", "goods"
    DIGITAL = "digital", "digital"
    EXPERIENCE = "experience", "experience"
    TICKET = "ticket", "ticket"
    COUPON = "coupon", "coupon"


class Product(models.Model):
    """A catalog listing (maps to the frontend ``Product`` type)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
        "creator.Creator",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="products",
    )
    type = models.CharField(max_length=16, choices=ProductType.choices)
    title = models.CharField(max_length=120)
    # Catalog display price in whole KRW (integer currency). Not a settlement.
    price = models.PositiveIntegerField(default=0)
    meta = models.CharField(max_length=120, blank=True, default="")
    media_url = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["creator", "-created_at"]),
            models.Index(fields=["type"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the product."""
        return f"{self.type}:{self.title}"
