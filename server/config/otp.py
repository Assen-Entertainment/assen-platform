"""Phone OTP send/verify adapter boundary + a local mock (ASS-98 / ASS-257).

Phone OTP is the approved signup provider (Company-OS
``20_Operations/Fan_Signup_Privacy_Policy.md``). Real SMS delivery sits behind a
later infrastructure/PII gate, so we ship the :class:`OtpSender` boundary and a
deterministic mock — the signup flow can be built and tested without an SMS
account or storing a real phone number.

Security contract (ASS-257): the three controls a production adapter MUST enforce
are codified on the boundary *and implemented by the mock* so they are testable
before a real adapter exists — **code expiry** (short TTL), **single use** (a
verified code is burned), and **attempt lockout** (bounded wrong guesses per
number, then a temporary lock). See :class:`OtpSender` for the full contract.

Runtime honesty — NOT enforced by the live mock flow (F3): the three controls are
verified by unit tests against a *single* :class:`MockOtpSender` instance, but the
live API builds a **fresh** sender per request (:func:`apps.identity.api._otp_sender`),
so no armed-code state survives from ``send`` to a later ``verify`` — the verify
falls back to the stateless deterministic comparison (:meth:`MockOtpSender.verify`),
which has no expiry, no single-use burn, and no lockout. Real enforcement therefore
belongs to the production SMS adapter backed by a **shared store** (Redis/DB) that
holds the armed state across requests and workers — never to this mock. This is not a
production exposure: prod runs with ``ENABLE_MOCK_FAN_OTP=False``, so the mock is never
constructed and the signup/login surface fails closed (503) instead of trusting an
unenforced code — security impact of the mock's un-enforced runtime path is zero.

Privacy: the phone number is never persisted by this layer; callers store only a
hash (개인정보 최소 수집). The mock derives a deterministic code from the number
via HMAC so tests are reproducible, and never logs or transmits it.

Lives in ``config/`` (infrastructure, no model), mirroring ``config/storage.py``.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

# The contract parameters a production adapter MUST honour; the mock uses the same
# defaults so a test exercises the real numbers. TTL is the OWASP-style short
# window; lockout bounds brute force *beneath* the per-IP request throttle
# (config.throttle), which limits request rate but not guess rate.
OTP_TTL_SECONDS = 180  # code valid for 3 minutes after send
OTP_MAX_ATTEMPTS = 5  # wrong guesses per armed code before…
OTP_LOCK_SECONDS = 300  # …a 5-minute lock on that number


class OtpError(Exception):
    """Raised when an OTP cannot be sent or verified."""


class OtpSender(ABC):
    """Boundary for sending and verifying a phone one-time passcode.

    Security contract — a production adapter MUST enforce all three (the mock does,
    so they are testable now; HUMAN-REVIEW-REQUIRED for the real SMS adapter behind
    the infra/PII gate):

    - **Code expiry.** A code is valid only for a short TTL (:data:`OTP_TTL_SECONDS`);
      an expired code verifies as false. A stateless HMAC code (see
      :meth:`MockOtpSender.code_for`) never expires and must never back production
      on its own.
    - **Single use.** A code is consumed on first successful verify and cannot be
      replayed; a verified code is burned even on a retried request.
    - **Attempt lockout.** Bounded verify attempts per number
      (:data:`OTP_MAX_ATTEMPTS`), then a temporary lock (:data:`OTP_LOCK_SECONDS`),
      so the 6-digit space cannot be brute-forced. Defence in depth *beneath* the
      per-IP request throttle on the endpoints (config.throttle).

    The contract binds to a *sent* code: :meth:`send` arms it and :meth:`verify`
    then enforces expiry/single-use/lockout against that armed state. The mock keeps
    this state in memory (per instance); the real adapter keeps it in a shared store
    (Redis/DB) so it holds across requests and workers.
    """

    @abstractmethod
    def send(self, *, phone: str) -> None:
        """Send (or arrange) an OTP for ``phone``; raise :class:`OtpError` on failure."""
        raise NotImplementedError

    @abstractmethod
    def verify(self, *, phone: str, code: str) -> bool:
        """Return whether ``code`` is the valid OTP for ``phone``.

        Enforces the class contract: an expired, already-consumed, or locked-out
        code verifies as ``False`` even when the digits match.
        """
        raise NotImplementedError


@dataclass
class _OtpEntry:
    """In-memory state for one armed code (mock only; real adapter uses a store)."""

    code: str
    issued_at: float
    attempts: int = 0
    consumed: bool = False
    locked_until: float | None = None


class MockOtpSender(OtpSender):
    """Deterministic local OTP for dev/tests — no real SMS, no number stored.

    The code is an HMAC of the phone number under a dev secret, so a test can
    derive the expected code without any out-of-band delivery. Not for production:
    a real adapter delegates to an SMS provider and persists the armed-code state
    in a shared store.

    State model: :meth:`send` arms a code (records issue time, clears attempts /
    lock / consumed); :meth:`verify` then enforces expiry, single-use, and lockout
    against that armed entry. State lives in ``self._entries`` — per instance, so it
    is isolated between senders (and, in the live API where each request builds a
    fresh sender, does not span requests; the real adapter's shared store does).

    Backward-compatible convenience: when a number has **no** armed entry on this
    instance (``send`` was never called here), :meth:`verify` falls back to a plain
    deterministic comparison against :meth:`code_for`. That keeps unit tests that
    call ``verify`` without a preceding ``send`` working; the real adapter has no
    such fallback (it always verifies a sent, stateful code).
    """

    def __init__(
        self,
        *,
        secret: str = "assen-dev-otp",
        ttl_seconds: int = OTP_TTL_SECONDS,
        max_attempts: int = OTP_MAX_ATTEMPTS,
        lock_seconds: int = OTP_LOCK_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        store: dict[str, _OtpEntry] | None = None,
    ) -> None:
        """Bind the mock to a dev secret + the contract knobs (overridable in tests).

        ``clock`` is injectable so a test can advance time to exercise expiry/lockout
        deterministically; ``store`` is injectable so a test can share or isolate the
        armed-code state.
        """
        self._secret = secret.encode("utf-8")
        self._ttl = ttl_seconds
        self._max_attempts = max_attempts
        self._lock_seconds = lock_seconds
        self._clock = clock
        self._entries: dict[str, _OtpEntry] = {} if store is None else store

    def code_for(self, phone: str) -> str:
        """Return the deterministic 6-digit code for ``phone`` (tests/dev only)."""
        digest = hmac.new(self._secret, phone.encode("utf-8"), hashlib.sha256)
        return str(int(digest.hexdigest()[:8], 16) % 1_000_000).zfill(6)

    def send(self, *, phone: str) -> None:
        """Arm a fresh code for ``phone`` (derivable via :meth:`code_for` in dev).

        A resend supersedes any prior challenge: it refreshes the TTL and clears the
        attempt count, lock, and consumed flag so the newest code is the live one.
        """
        if not phone:
            raise OtpError("phone is required.")
        self._entries[phone] = _OtpEntry(
            code=self.code_for(phone), issued_at=self._clock()
        )

    def verify(self, *, phone: str, code: str) -> bool:
        """Verify ``code`` for ``phone``, enforcing expiry / single-use / lockout.

        With an armed entry: a locked, consumed, or expired code returns ``False``;
        a correct code is burned (single-use) and returns ``True``; a wrong code
        increments the attempt count and locks the number once the cap is reached.
        With no armed entry (never sent on this instance): falls back to the
        deterministic comparison (see the class docstring).
        """
        entry = self._entries.get(phone)
        if entry is None:
            return hmac.compare_digest(self.code_for(phone), code)
        now = self._clock()
        if entry.locked_until is not None and now < entry.locked_until:
            return False  # attempt lockout in force
        if entry.consumed:
            return False  # single-use: already burned
        if now - entry.issued_at > self._ttl:
            return False  # expired
        if hmac.compare_digest(entry.code, code):
            entry.consumed = True  # burn on first success
            return True
        entry.attempts += 1
        if entry.attempts >= self._max_attempts:
            entry.locked_until = now + self._lock_seconds
        return False
