"""Acceptance tests for the local mock signed-URL adapter.

Covers: a freshly issued URL verifies, an expired URL fails, a tampered key or
signature fails, and non-positive expiry is rejected.
"""

from __future__ import annotations

import time

import pytest

from config.storage import LocalMockSignedUrlAdapter


def _adapter() -> LocalMockSignedUrlAdapter:
    """Create a signer with a fixed test secret."""
    return LocalMockSignedUrlAdapter(secret="test-secret")


def test_freshly_signed_url_verifies() -> None:
    """A URL issued with a future expiry verifies as valid."""
    adapter = _adapter()
    signed = adapter.generate(object_key="cheki/abc.jpg", expires_in=60)
    assert adapter.verify(signed.url) is True
    assert signed.expires_at > int(time.time())


def test_expired_url_fails_verification() -> None:
    """A URL whose expiry is in the past does not verify."""
    adapter = _adapter()
    # Issue with a tiny lifetime, then move past it.
    signed = adapter.generate(object_key="cheki/abc.jpg", expires_in=1)
    # Re-sign with an already-past expiry to simulate elapsed time deterministically.
    past = int(time.time()) - 5
    sig = adapter._sign("cheki/abc.jpg", past)
    expired_url = f"https://mock-store.local/cheki/abc.jpg?key=cheki/abc.jpg&expires={past}&sig={sig}"
    assert adapter.verify(expired_url) is False
    # Sanity: the freshly issued one is still valid.
    assert adapter.verify(signed.url) is True


def test_tampered_signature_fails() -> None:
    """Altering the signature or key breaks verification."""
    adapter = _adapter()
    signed = adapter.generate(object_key="cheki/abc.jpg", expires_in=60)
    tampered = signed.url.replace("sig=", "sig=deadbeef")
    assert adapter.verify(tampered) is False


def test_swapped_object_key_fails() -> None:
    """A signature minted for one object does not authorise another."""
    adapter = _adapter()
    signed = adapter.generate(object_key="chekiabc.jpg", expires_in=60)
    # Swap the signed key query param to a different object; the signature, bound
    # to the original key, must no longer verify.
    swapped = signed.url.replace("key=chekiabc.jpg", "key=safetysecret.jpg")
    assert "key=safetysecret.jpg" in swapped
    assert adapter.verify(swapped) is False


def test_non_positive_expiry_rejected() -> None:
    """Requesting a non-positive lifetime is an error."""
    adapter = _adapter()
    with pytest.raises(ValueError):
        adapter.generate(object_key="x", expires_in=0)
