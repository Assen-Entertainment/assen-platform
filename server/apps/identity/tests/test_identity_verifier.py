"""Tests for the IdentityVerifier boundary (본인인증 / 19+ seam).

The mock verifier approves inline (no provider, no PII); a real adapter plugs in
behind the same boundary — returning a VerificationChallenge from ``start`` and
verifying the client's provider token in ``confirm``. Gated behind
``ENABLE_MOCK_KYC`` (None in production — fail-closed).
"""

from __future__ import annotations

import pytest
from django.test import override_settings

from apps.identity.models import Account, Role
from config.identity_verify import (
    MockIdentityVerifier,
    VerificationChallenge,
    identity_verifier,
)

pytestmark = pytest.mark.django_db


def _account() -> Account:
    """Create a plain fan account (the mock never consults it)."""
    return Account.objects.create(role=Role.FAN.value, nickname="지망생")


def test_mock_start_returns_no_challenge() -> None:
    """The mock has no provider handshake → start returns None."""
    assert MockIdentityVerifier().start(account=_account()) is None


def test_mock_confirm_ignores_token_and_passes() -> None:
    """The mock confirms adult regardless of a provider token (consults none)."""
    verifier = MockIdentityVerifier()
    account = _account()
    assert verifier.confirm(account=account).adult is True
    assert verifier.confirm(account=account, token="imp_123").adult is True


def test_verification_challenge_carries_handshake_refs() -> None:
    """VerificationChallenge holds opaque provider handshake params (no PII)."""
    challenge = VerificationChallenge(
        provider="portone", redirect_url="https://x/verify", session_id="s-1"
    )
    assert challenge.provider == "portone"
    assert challenge.redirect_url == "https://x/verify"
    assert challenge.session_id == "s-1"


@override_settings(ENABLE_MOCK_KYC=True)
def test_identity_verifier_returns_mock_when_enabled() -> None:
    """With the mock flag on, the accessor returns the deterministic mock."""
    assert isinstance(identity_verifier(), MockIdentityVerifier)


@override_settings(ENABLE_MOCK_KYC=False)
def test_identity_verifier_is_none_when_disabled() -> None:
    """No real provider wired → fail closed (None), mirroring the payment gateway."""
    assert identity_verifier() is None
