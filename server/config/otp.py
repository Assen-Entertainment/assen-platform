"""Phone OTP send/verify adapter boundary + a local mock (ASS-98 v0).

Phone OTP is the approved signup provider (Company-OS
``20_Operations/Fan_Signup_Privacy_Policy.md``). Real SMS delivery sits behind a
later infrastructure/PII gate, so P0 ships only the :class:`OtpSender` boundary
and a deterministic mock — the signup flow can be built and tested without an SMS
account or storing a real phone number.

Privacy: the phone number is never persisted by this layer; callers store only a
hash (개인정보 최소 수집). The mock derives a deterministic code from the number
via HMAC so tests are reproducible, and never logs or transmits it.

Lives in ``config/`` (infrastructure, no model), mirroring ``config/storage.py``.
"""

from __future__ import annotations

import hashlib
import hmac
from abc import ABC, abstractmethod


class OtpError(Exception):
    """Raised when an OTP cannot be sent or verified."""


class OtpSender(ABC):
    """Boundary for sending and verifying a phone one-time passcode."""

    @abstractmethod
    def send(self, *, phone: str) -> None:
        """Send (or arrange) an OTP for ``phone``; raise :class:`OtpError` on failure."""
        raise NotImplementedError

    @abstractmethod
    def verify(self, *, phone: str, code: str) -> bool:
        """Return whether ``code`` is the valid OTP for ``phone``."""
        raise NotImplementedError


class MockOtpSender(OtpSender):
    """Deterministic local OTP for dev/tests — no real SMS, no number stored.

    The code is an HMAC of the phone number under a dev secret, so a test can
    derive the expected code without any out-of-band delivery. Not for
    production: a real adapter delegates to an SMS provider and rate-limits.
    """

    def __init__(self, *, secret: str = "assen-dev-otp") -> None:
        """Bind the mock to a dev secret used to derive deterministic codes."""
        self._secret = secret.encode("utf-8")

    def code_for(self, phone: str) -> str:
        """Return the deterministic 6-digit code for ``phone`` (tests/dev only)."""
        digest = hmac.new(self._secret, phone.encode("utf-8"), hashlib.sha256)
        return str(int(digest.hexdigest()[:8], 16) % 1_000_000).zfill(6)

    def send(self, *, phone: str) -> None:
        """No-op send: the code is derivable via :meth:`code_for` in dev/tests."""
        if not phone:
            raise OtpError("phone is required.")

    def verify(self, *, phone: str, code: str) -> bool:
        """Constant-time compare ``code`` against the derived code for ``phone``."""
        return hmac.compare_digest(self.code_for(phone), code)
