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
