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
from datetime import timedelta
from typing import Any

from django.db import models

from config.payment import PaymentProvenance, PricingKind

# Mock billing cycle length — the cadence of the display anchor AND the mock
# renewal worker (apps.membership.tasks). There is no real recurring billing (B7
# gated); this only advances mock periods/settlements.
BILLING_CYCLE = timedelta(days=30)


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
    # Explicit price intent (ASS-297): PAID by default, so a price-0 tier is a
    # placeholder, not free. Only a FREE tier may be acquired via /subscriptions/free.
    pricing_kind = models.CharField(
        max_length=8, choices=PricingKind.choices, default=PricingKind.PAID
    )
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
    """Subscription states surfaced to the fan (billing state machine, Codex #5).

    ``active`` = entitled (a non-cancelled active sub auto-renews at period end; a
    cancelled one — ``cancelled_at`` set — stays active/entitled until its
    ``current_period_end``, then the billing worker expires it). ``expired`` = a
    period ended without renewal (the terminal state the worker writes for a
    cancelled/non-renewing sub). ``cancelled`` = an immediately-terminated sub (no
    end-of-period grace); kept for completeness and legacy rows. Only ``active`` is
    ever entitled (see :func:`apps.membership.services.active_subscription`).
    """

    ACTIVE = "active", "active"
    CANCELLED = "cancelled", "cancelled"
    EXPIRED = "expired", "expired"


class Subscription(models.Model):
    """A fan's mock membership subscription. MOCK: no money moves (B7 gated).

    **Immutable agreed terms (#16):** ``agreed_price``/``agreed_period``/
    ``agreed_tier_name`` snapshot the tier's terms at subscribe (and re-snapshot at
    tier change), so a creator later editing the (mutable) tier price/period can
    never silently re-term an existing member — the subscription is billed and
    displayed on its own agreed terms, not the tier's live ones.

    **Billing state machine (#5):** ``current_period_end`` is the entitlement cutoff.
    End-of-period cancellation ("해지 예정"): :meth:`cancel <apps.membership.api>`
    records ``cancelled_at`` but keeps ``status = active`` (still entitled) until
    ``current_period_end``; the mock billing worker (apps.membership.tasks) then
    expires it. A non-cancelled active sub is instead RENEWED by the worker (mock
    settlement + advanced period). The API exposes a derived ``cancel_scheduled``
    flag so the web renders "해지 예정".
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fan = models.ForeignKey(
        "identity.Account", on_delete=models.CASCADE, related_name="subscriptions"
    )
    # Kept CASCADE by design: a subscription with real settlement history is still
    # protected from tier deletion, because its PaymentAttempt rows are PROTECT
    # (apps.payments.models) — deleting the tier would cascade to the subscription,
    # which the protected attempt then blocks (ProtectedError). ``studio_delete_tier``
    # catches that and soft-archives the tier instead (#16). Only a bare subscription
    # with no financial history (never produced by the API — every subscribe path
    # ledgers an attempt) can still be cascade-removed with its tier. The subscription
    # additionally carries its own agreed-terms snapshot, so it never depends on the
    # tier row surviving to render its price/period.
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
    # Immutable agreed-terms snapshot (#16), captured at subscribe and re-captured at
    # tier change. These — NOT the tier's live, mutable price/period — are what the
    # member is billed and shown, so editing the tier never re-terms existing members.
    # NULL/blank only on legacy rows predating this snapshot; those fall back to the
    # live tier at read time (best available value, never a guess — mirrors
    # PaymentProvenance.LEGACY_UNKNOWN).
    agreed_price = models.PositiveIntegerField(null=True, blank=True)
    agreed_period = models.CharField(max_length=8, blank=True, default="")
    agreed_tier_name = models.CharField(max_length=40, blank=True, default="")
    # Mock billing anchor (display only; no PG/settlement — B7 gated). NULL for a
    # free membership (ASS-297): a free grant has no next charge, so a fabricated
    # date is never stored or shown.
    next_billing_date = models.DateField(null=True, blank=True)
    # Entitlement cutoff for the billing state machine (#5): the moment the current
    # paid period ends. The worker RENEWS (advances this + mock settlement) an active
    # non-cancelled sub past this instant, and EXPIRES a cancelled/non-renewing one.
    # NULL for a free/legacy membership (no billing period — the worker skips it).
    current_period_end = models.DateTimeField(null=True, blank=True)
    # Set when the fan schedules end-of-period cancellation; status stays active.
    cancelled_at = models.DateTimeField(null=True, blank=True)
    # How this ACTIVE membership was settled (ASS-298). Set explicitly on every
    # write (mock/free); the LEGACY_UNKNOWN default only ever applies to rows that
    # predate this column — never a guessed value.
    payment_provenance = models.CharField(
        max_length=16,
        choices=PaymentProvenance.choices,
        default=PaymentProvenance.LEGACY_UNKNOWN,
    )

    class Meta:
        indexes = [
            models.Index(fields=["fan", "-started_at"]),
            models.Index(fields=["payment_provenance"]),
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
