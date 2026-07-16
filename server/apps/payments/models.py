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
from typing import Any

from django.db import models


class AppendOnlyViolation(Exception):
    """Raised when code attempts to mutate a persisted reversal ledger row.

    Surfaces the append-only invariant as a hard failure rather than letting a
    silent update corrupt financial history (mirrors
    :class:`apps.event_log.models.AppendOnlyViolation`).
    """


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


class PaymentProvider(models.TextChoices):
    """Which settlement rail an attempt went through (ASS-298).

    ``mock`` = the deterministic dev mock; ``free`` = an explicit free grant
    (ASS-297, no rail); ``external`` = a real PG (future — never written today).
    """

    MOCK = "mock", "mock"
    FREE = "free", "free"
    EXTERNAL = "external", "external"


class PaymentAttemptStatus(models.TextChoices):
    """Lifecycle of a single payment attempt (ASS-298)."""

    PENDING = "pending", "pending"
    SUCCEEDED = "succeeded", "succeeded"
    FAILED = "failed", "failed"
    REFUNDED = "refunded", "refunded"


class PaymentAttempt(models.Model):
    """Append-only payment-attempt ledger, designed before a real PG (ASS-298).

    Records how an ``Order``/``Subscription`` was settled so a paid/active record
    can always answer "which attempt settled this" ahead of a real PG. Today only
    ``mock``/``free`` attempts are written. By construction it holds NO card data —
    only an opaque provider transaction id, amount, currency, and status. Linked
    1:N to exactly one of ``Order`` or ``Subscription`` (the XOR constraint below);
    a refund attempt points at the capture it reverses via ``original_attempt``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "commerce.Order",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="payment_attempts",
    )
    # PROTECT (not CASCADE): a settlement ledger is financial history and must never
    # be erased by deleting its subscription (#16). Combined with the XOR constraint
    # (a null subscription would break it, so SET_NULL is not an option), PROTECT is
    # the correct guard — deleting a subscription (or, transitively, its tier) that
    # has attempts raises ProtectedError; ``studio_delete_tier`` soft-archives instead.
    subscription = models.ForeignKey(
        "membership.Subscription",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_attempts",
    )
    # A sale that settled on a hosted commerce SaaS (apps.commerce_bridge). Assen does
    # not own the transaction; this attribution row (provider=external) credits the
    # creator's earning. The third arm of the XOR below.
    external_order = models.ForeignKey(
        "commerce_bridge.ExternalCommerceOrder",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="payment_attempts",
    )
    provider = models.CharField(max_length=16, choices=PaymentProvider.choices)
    # Opaque PG/mock transaction id — NEVER a PAN. Blank until a provider assigns one.
    provider_txn_id = models.CharField(max_length=128, blank=True, default="")
    # Authorized amount snapshot in whole KRW. NOT a settlement figure (mock/free today).
    authorized_amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="KRW")
    status = models.CharField(
        max_length=16,
        choices=PaymentAttemptStatus.choices,
        default=PaymentAttemptStatus.PENDING,
    )
    # Idempotency echo of the parent order's key (the parent owns dedup); indexed for
    # ledger lookup, not uniquely constrained here.
    idempotency_key = models.CharField(
        max_length=64, null=True, blank=True, default=None
    )
    # A refund attempt references the capture it reverses (real-PG semantics: a
    # refund is a new txn pointing at the original). SET_NULL keeps the refund row
    # if the capture is ever purged.
    original_attempt = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="refunds",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "-created_at"]),
            models.Index(fields=["subscription", "-created_at"]),
            models.Index(fields=["external_order", "-created_at"]),
            models.Index(fields=["provider", "status"]),
        ]
        constraints = [
            # An attempt settles exactly one target — an order XOR a subscription XOR an
            # external (hosted-commerce) order, never more than one and never none.
            # Materialised by the app's migration.
            models.CheckConstraint(
                # ``condition=`` (not the ``check=`` removed in Django 6.0); the new
                # kwarg name is accepted since Django 5.1, so this stays valid on both.
                condition=(
                    models.Q(
                        order__isnull=False,
                        subscription__isnull=True,
                        external_order__isnull=True,
                    )
                    | models.Q(
                        order__isnull=True,
                        subscription__isnull=False,
                        external_order__isnull=True,
                    )
                    | models.Q(
                        order__isnull=True,
                        subscription__isnull=True,
                        external_order__isnull=False,
                    )
                ),
                name="payment_attempt_exactly_one_target",
            ),
        ]

    def __str__(self) -> str:
        """Identify the attempt by provider + status."""
        return f"attempt:{self.provider}:{self.status}"


class PaymentReversalStatus(models.TextChoices):
    """Lifecycle of a single reversal (void/refund) attempt (#3 BLOCKER-seam).

    ``pending`` = the gateway needs an out-of-band step before the reversal settles;
    ``succeeded`` = the charge was reversed (money returned); ``failed`` = the
    reversal was declined. The mock only ever returns ``succeeded``; the other states
    exist so the enum is stable when a real async PG is wired.
    """

    PENDING = "pending", "pending"
    SUCCEEDED = "succeeded", "succeeded"
    FAILED = "failed", "failed"


class PaymentReversal(models.Model):
    """Append-only reversal (void/refund) ledger for a settled charge (#3 seam).

    When a fan cancellation or an operator-accepted refund reverses a PAID order,
    the gateway's void/refund op is recorded here — durably and immutably linked to
    the settlement it reverses (``original_attempt``, PROTECT). Designed *before* a
    real PG so a cancelled/refunded order can always answer "was the original capture
    reversed, and did it settle" ahead of one existing: today the code cancels +
    restocks while money never moves, so this ledger is what a real PG later
    reconciles against. Only ``mock`` reversals are written today; by construction it
    holds NO card data — only an opaque reversal ref, amount, currency, status, and a
    reason. **Immutable**: a row is written once and never updated (``save`` refuses a
    second write); a corrective reversal is a *new* row, never a mutation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # PROTECT (not CASCADE): the reversal points at the capture it reverses; that
    # settlement is financial history and must never be erased out from under an
    # existing reversal (mirrors PaymentAttempt.subscription's PROTECT from #16).
    original_attempt = models.ForeignKey(
        "payments.PaymentAttempt",
        on_delete=models.PROTECT,
        related_name="reversals",
    )
    provider = models.CharField(max_length=16, choices=PaymentProvider.choices)
    # Opaque PG/mock reversal transaction id — NEVER a PAN. Blank until assigned.
    reversal_ref = models.CharField(max_length=128, blank=True, default="")
    # Reversed amount snapshot in whole KRW. NOT a settlement figure (mock today).
    amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="KRW")
    status = models.CharField(
        max_length=16,
        choices=PaymentReversalStatus.choices,
        default=PaymentReversalStatus.PENDING,
    )
    # Why the charge was reversed (e.g. "order_cancelled", "refund_accepted").
    reason = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["original_attempt", "-created_at"]),
            models.Index(fields=["provider", "status"]),
        ]
        constraints = [
            # At most one SUCCEEDED reversal per original settlement — a second
            # cancel/refund-accept of the same order must never durably double-reverse
            # the same capture. A declined/pending reversal may be retried, so only
            # the succeeded state is constrained. Materialised by the app's migration.
            models.UniqueConstraint(
                fields=["original_attempt"],
                condition=models.Q(status="succeeded"),
                name="uniq_succeeded_reversal_per_attempt",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Allow the first insert; reject any re-save of an existing row.

        ``self._state.adding`` is True only for the initial insert. A second
        ``save`` (an update) means someone is mutating the reversal ledger, which the
        append-only contract forbids.
        """
        if not self._state.adding:
            raise AppendOnlyViolation(
                f"PaymentReversal {self.pk} is append-only and cannot be modified. "
                "Record a new reversal instead."
            )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Identify the reversal by provider + status."""
        return f"reversal:{self.provider}:{self.status}"
