"""Tests for the payment-gateway charge boundary (ASS-298 seam).

A :class:`~config.payment.PaymentGateway` authorizes + captures a charge; the
deterministic mock approves inline and is gated behind ``ENABLE_MOCK_PAYMENT``
(``None`` in production — fail-closed, so a charge-less order can never be PAID).
"""

from __future__ import annotations

from django.test import override_settings

from config.payment import (
    ChargeStatus,
    MockPaymentGateway,
    PaymentCharge,
    PaymentProvenance,
    payment_gateway,
)


def test_mock_gateway_approves_inline() -> None:
    """The mock returns an approved charge whose ref matches the ledger's id."""
    charge = MockPaymentGateway().charge(
        order_id="o-1", amount=9900, currency="KRW"
    )
    assert charge.status is ChargeStatus.APPROVED
    assert charge.approved is True
    assert charge.provenance is PaymentProvenance.MOCK
    # The ref must match ``payments.record_mock_settlement``'s ``mock_{id}`` so
    # the gateway and the ledger agree on the same transaction id.
    assert charge.provider_ref == "mock_o-1"


def test_payment_charge_approved_property() -> None:
    """`approved` is True only for the APPROVED status (pending/failed → False)."""
    ref, prov = "r", PaymentProvenance.MOCK
    assert PaymentCharge(ChargeStatus.APPROVED, ref, prov).approved is True
    assert PaymentCharge(ChargeStatus.PENDING, ref, prov).approved is False
    assert PaymentCharge(ChargeStatus.FAILED, ref, prov).approved is False


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_payment_gateway_returns_mock_when_enabled() -> None:
    """With the mock flag on, the accessor returns the deterministic mock."""
    assert isinstance(payment_gateway(), MockPaymentGateway)


@override_settings(ENABLE_MOCK_PAYMENT=False)
def test_payment_gateway_is_none_when_disabled() -> None:
    """No real PG wired → fail closed (None), mirroring payment_tokenizer."""
    assert payment_gateway() is None
