"""Payment-method tokenization adapter boundary + a local mock (R3).

Mirrors ``config/otp.py`` and ``config/identity_verify.py``: this ships only the
:class:`PaymentTokenizer` boundary and a deterministic mock, so the saved-payment-
method flow can be built and tested without a real PG or ever storing a card PAN.

법무/보안 경계 (R3 계획 §R4, PCI): a real card PAN/expiry/cvc is NEVER stored, and the
mock NEVER returns one. The tokenizer takes a mock card number, derives ONLY the last
4 digits (for display), discards everything else, and returns brand + last4 + a
placeholder token — exactly what the model persists. Real PG tokenization (PCI scope)
is a separate 대표·법무·PG gate; when wired it replaces :class:`MockPaymentTokenizer`
behind this same boundary and still returns only brand + last4 + the PG's billing
token, never the PAN.

Lives in ``config/`` (infrastructure, no model coupling), mirroring ``config/otp.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.conf import settings
from django.db import models

from config.errors import ApiError, ErrorCode


class PaymentProvenance(models.TextChoices):
    """Where a PAID/ACTIVE record's settlement actually came from (ASS-298).

    Recorded on ``Order``/``Subscription`` so a paid/active record can always
    answer "how was this settled" before a real PG exists. Pre-ASS-298 rows are
    never guessed — they backfill to :attr:`LEGACY_UNKNOWN`. Today only
    :attr:`MOCK` (deterministic mock, ``ENABLE_MOCK_PAYMENT``) and :attr:`FREE`
    (an explicit free grant, ASS-297) are ever written; :attr:`EXTERNAL` is
    reserved for when a real PG replaces the mock behind the same flag.
    """

    FREE = "free", "free"
    MOCK = "mock", "mock"
    EXTERNAL = "external", "external"
    LEGACY_UNKNOWN = "legacy_unknown", "legacy unknown"


class PricingKind(models.TextChoices):
    """Explicit price intent for an offering (ASS-297).

    Distinguishes a genuinely free product/tier (:attr:`FREE`) from a default-0
    placeholder ``price`` on a paid offering (:attr:`PAID`). Defaults to
    :attr:`PAID` everywhere, so a price-0 row is never treated as free — a free
    offering is only ever created by an explicit studio action, and acquiring it
    goes through the dedicated free-grant path, never the ``amount==0`` bypass the
    payment gate forbids.
    """

    PAID = "paid", "paid"
    FREE = "free", "free"


class PaymentError(Exception):
    """Raised when a payment method cannot be tokenized."""


@dataclass(frozen=True)
class TokenizedCard:
    """The minimal, non-sensitive result of tokenizing a card.

    ``brand`` + ``last4`` are display-only; ``pg_token`` is an opaque placeholder
    standing in for a real PG billing token. No PAN/expiry/cvc is present — by
    construction the only card-derived value that survives is the last 4 digits.
    """

    brand: str
    last4: str
    pg_token: str


class PaymentTokenizer(ABC):
    """Boundary for turning card entry into a stored, non-sensitive payment method.

    The single method receives a (mock) card number only to derive the display
    ``last4``; it MUST NOT persist or return the PAN. A real adapter delegates to a
    PG's tokenization (the PAN goes to the PG, never our DB) and returns the PG's
    billing token in :attr:`TokenizedCard.pg_token`.

    TODO (real PG — HUMAN-REVIEW-REQUIRED, 대표·법무·PG gate, PCI): a production adapter
    exchanges a PG-widget token (raw PAN never transits our server — R4) for a stored
    billing token, returning brand + last4 + that token.
    """

    @abstractmethod
    def tokenize(self, *, card_number: str, brand: str) -> TokenizedCard:
        """Derive a :class:`TokenizedCard` from a card; raise on failure.

        Only the last 4 digits of ``card_number`` may survive — the full number is
        discarded and never stored or logged.
        """
        raise NotImplementedError


class MockPaymentTokenizer(PaymentTokenizer):
    """Deterministic local tokenizer for dev/tests — no real PG, no PAN stored.

    Discards the input card entirely except its last 4 digits and returns a
    deterministic mock token. Not for production: a real adapter delegates to a PG.
    Mirrors :class:`~config.otp.MockOtpSender`, which receives the phone but never
    stores it.
    """

    def tokenize(self, *, card_number: str, brand: str) -> TokenizedCard:
        """Keep only brand + last4 from the card; the PAN is discarded here."""
        digits = "".join(ch for ch in card_number if ch.isdigit())
        if len(digits) < 4:
            raise PaymentError("A valid card number is required.")
        last4 = digits[-4:]
        # The mock token is derived from last4 only (never the PAN) so it carries no
        # sensitive data. Uniqueness is not required (no unique constraint on it).
        return TokenizedCard(
            brand=brand or "CARD", last4=last4, pg_token=f"mock_tok_{last4}"
        )


def payment_tokenizer() -> PaymentTokenizer | None:
    """Return the configured payment tokenizer, or ``None`` when none is wired.

    The deterministic mock is gated behind ``ENABLE_MOCK_PAYMENT`` (off in
    production) so it can never back a real charge. With no real PG wired yet,
    production returns ``None`` and the payment-method surface fails closed (503)
    rather than pretend a card was tokenized — mirroring ``_otp_sender`` in
    :mod:`apps.identity.api`.
    """
    if settings.ENABLE_MOCK_PAYMENT:
        return MockPaymentTokenizer()
    return None


def require_payment_available() -> None:
    """Fail closed (503) when no payment path can actually settle a charge.

    Order / subscription creation must never mint a ``PAID``/``ACTIVE`` record when
    there is no way to take money. Until a real PG is wired, the only settleable
    state is the deterministic mock (dev/test/demo), gated by ``ENABLE_MOCK_PAYMENT``.

    Gated on the flag, NOT on :func:`payment_tokenizer`: tokenization is not
    authorization/capture, so a real tokenizer would still let a charge-free
    ``PAID`` slip through (ASS-286). This is containment — "no false paid/active" —
    not a PG-ready charge flow. Free products/tiers are a separate, explicit grant
    (ASS-297), never a zero-amount bypass here.
    """
    if not settings.ENABLE_MOCK_PAYMENT:
        raise ApiError(
            503,
            "결제가 아직 준비되지 않았어요.",
            code=ErrorCode.PAYMENTS_UNAVAILABLE,
        )


class ChargeStatus(models.TextChoices):
    """Outcome of a payment charge attempt through a :class:`PaymentGateway`.

    ``approved`` = authorized + captured (money is taken); ``pending`` = the PG
    needs an out-of-band step (redirect/webhook) before it settles, so the order
    must stay unsettled until a later confirm; ``failed`` = declined. The mock
    only ever returns ``approved`` (deterministic, synchronous); ``pending`` /
    ``failed`` exist so the enum is stable when a real async PG is wired.
    """

    APPROVED = "approved", "approved"
    PENDING = "pending", "pending"
    FAILED = "failed", "failed"


@dataclass(frozen=True)
class PaymentCharge:
    """The non-sensitive result of charging an order through a payment gateway.

    ``provider_ref`` is the gateway's own transaction reference (a mock id today,
    a real PG's imp_uid/tid when wired) — never a card PAN. ``provenance`` records
    which rail settled it (mock today; external for a real PG) so the ledger and
    the order's ``payment_provenance`` agree.
    """

    status: ChargeStatus
    provider_ref: str
    provenance: PaymentProvenance

    @property
    def approved(self) -> bool:
        """Whether the charge authorized + captured (money was actually taken)."""
        return self.status == ChargeStatus.APPROVED


@dataclass(frozen=True)
class PaymentRefund:
    """The non-sensitive result of reversing a settled charge through a gateway.

    Mirrors :class:`PaymentCharge` for the money-*out* direction: ``reversal_ref``
    is the gateway's own reference for the void/refund transaction (a mock id today,
    a real PG's refund/cancel id when wired) — never a card PAN. ``provenance``
    records which rail processed it (mock today) so the reversal ledger and the
    original settlement agree. A refund is a *new* gateway transaction pointing back
    at the capture it reverses; recording it never mutates the capture. Reuses
    :class:`ChargeStatus` — ``approved`` means the reversal settled (money returned),
    ``pending`` means an out-of-band step is still owed, ``failed`` a decline.
    """

    status: ChargeStatus
    reversal_ref: str
    provenance: PaymentProvenance

    @property
    def approved(self) -> bool:
        """Whether the gateway reversed the charge (money was actually returned)."""
        return self.status == ChargeStatus.APPROVED


class PaymentGateway(ABC):
    """Boundary for authorizing + capturing a charge against a fan's order.

    Distinct from :class:`PaymentTokenizer` (which only saves a card): a gateway
    *takes money*. The single method captures a charge and returns a
    :class:`PaymentCharge` — never a PAN. A real adapter (포트원/토스 등) delegates to
    the PG's authorize/capture: a synchronous-capture PG returns ``approved``
    inline, while a redirect/webhook PG returns ``pending`` (the order stays
    unsettled until a later confirm — a follow-up to the order lifecycle).

    TODO (real PG — HUMAN-REVIEW-REQUIRED, 대표·법무·PG gate, PCI): a production
    adapter verifies + captures a PG-widget payment (the PAN never transits our
    server — R4) and returns the PG's reference + the approved/pending/failed
    status.
    """

    @abstractmethod
    def charge(
        self,
        *,
        order_id: str,
        amount: int,
        currency: str,
        idempotency_key: str | None = None,
    ) -> PaymentCharge:
        """Authorize + capture ``amount`` (whole KRW) for ``order_id``.

        ``idempotency_key`` is the order's client key (may be ``None``): a real PG
        uses it to dedup a retried capture so a network retry can never double-charge
        the same order. Returns the outcome. Must never persist or return a card PAN.
        """
        raise NotImplementedError

    def refund(
        self,
        *,
        order_id: str,
        amount: int,
        currency: str,
        original_ref: str,
        idempotency_key: str | None = None,
    ) -> PaymentRefund:
        """Reverse (void/refund) a previously captured charge for ``order_id``.

        Called when a fan cancellation or an operator-accepted refund reverses a
        settled order: ``original_ref`` is the gateway reference of the capture being
        reversed (the order's ``payment_ref``), and ``amount`` (whole KRW) is the sum
        to return. ``idempotency_key`` (the order's client key, may be ``None``) lets
        a real PG dedup a retried reversal so a network retry can never double-refund.
        Returns the outcome. Must never persist or return a card PAN.

        Unlike :meth:`charge`, this is a concrete default (not ``@abstractmethod``) so
        that pre-existing charge-only gateways remain valid — a gateway that never
        reverses need not implement it. **A production adapter MUST override it** to
        drive the PG's void/refund; the default fails loud rather than silently
        pretending a reversal happened.
        """
        raise NotImplementedError


class MockPaymentGateway(PaymentGateway):
    """Deterministic local gateway for dev/tests — approves inline, moves no money.

    Mirrors :class:`MockPaymentTokenizer`: it takes no card and returns a
    deterministic approved charge (``provider_ref = mock_{order_id}`` — the same
    id ``payments.record_mock_settlement`` ledgers) so the order flow can settle
    without a real PG. Not for production: a real adapter delegates to a PG.
    """

    def charge(
        self,
        *,
        order_id: str,
        amount: int,
        currency: str,
        idempotency_key: str | None = None,
    ) -> PaymentCharge:
        """Return a deterministic approved charge (no money moves)."""
        # amount/currency/idempotency_key are snapshotted on the order + ledger; the
        # mock does not consult them (nothing to authorize or dedup against).
        del amount, currency, idempotency_key
        return PaymentCharge(
            status=ChargeStatus.APPROVED,
            provider_ref=f"mock_{order_id}",
            provenance=PaymentProvenance.MOCK,
        )

    def refund(
        self,
        *,
        order_id: str,
        amount: int,
        currency: str,
        original_ref: str,
        idempotency_key: str | None = None,
    ) -> PaymentRefund:
        """Return a deterministic approved reversal (no money moves)."""
        # amount/currency/original_ref/idempotency_key are snapshotted on the reversal
        # ledger; the mock does not consult them (nothing to authorize or dedup).
        del amount, currency, original_ref, idempotency_key
        return PaymentRefund(
            status=ChargeStatus.APPROVED,
            reversal_ref=f"mock_reversal_{order_id}",
            provenance=PaymentProvenance.MOCK,
        )


def payment_gateway() -> PaymentGateway | None:
    """Return the configured payment gateway, or ``None`` when none is wired.

    The deterministic mock is gated behind ``ENABLE_MOCK_PAYMENT`` (off in
    production) so it can never back a real charge. With no real PG wired yet,
    production returns ``None`` and the order flow fails closed — mirroring
    :func:`payment_tokenizer` and :func:`require_payment_available`.
    """
    if settings.ENABLE_MOCK_PAYMENT:
        return MockPaymentGateway()
    return None
