"""Saved payment methods — brand + last4 + mock PG token only (R3).

법무/보안 경계 (R3 계획 §R4, PCI): this model NEVER stores a card PAN/expiry/cvc. The
only card-derived value persisted is the display ``last4``; ``pg_token`` is an opaque
placeholder for a real PG billing token (mock in dev). Real PG tokenization is a
대표·법무·PG gate (see :mod:`config.payment`).

Migrated app — ``migrate`` applies ``0001_initial``; regenerate with
``makemigrations`` when models change.
"""

from __future__ import annotations

import uuid

from django.db import models


class SavedPaymentMethod(models.Model):
    """A fan's saved payment method — display metadata + a mock token, no PAN."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        "identity.Account", on_delete=models.CASCADE, related_name="payment_methods"
    )
    # Card network/brand for display (e.g. "VISA"). Not sensitive.
    brand = models.CharField(max_length=20)
    # ONLY the last 4 digits — never the full PAN (PCI / 법무 경계). Display use only.
    last4 = models.CharField(max_length=4)
    # Opaque placeholder for a real PG billing token (mock in dev). Never a PAN.
    pg_token = models.CharField(max_length=128, blank=True, default="")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
        ]
        ordering = ["-created_at"]
        constraints = [
            # At most one primary method per owner. Partial unique on is_primary so
            # non-primary rows are unconstrained. Materialised by the app's
            # migration (applied by ``migrate``).
            models.UniqueConstraint(
                fields=["owner"],
                condition=models.Q(is_primary=True),
                name="uniq_primary_payment_method_per_owner",
            ),
        ]

    def __str__(self) -> str:
        """Identify the method by brand + last4 (never a full PAN)."""
        return f"card:{self.brand}****{self.last4}"
