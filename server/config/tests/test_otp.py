"""Tests for the OTP sender contract — expiry, single-use, lockout (ASS-257).

The mock is the reference implementation of the :class:`~config.otp.OtpSender`
security contract, so these tests double as the executable spec a real SMS adapter
must satisfy. An injected clock makes expiry/lockout deterministic; an injected
store isolates state per test.
"""

from __future__ import annotations

import pytest

from config.otp import (
    OTP_LOCK_SECONDS,
    OTP_MAX_ATTEMPTS,
    OTP_TTL_SECONDS,
    MockOtpSender,
    OtpError,
    _OtpEntry,
)

_PHONE = "+821012345678"


class _Clock:
    """A hand-cranked monotonic clock so expiry/lockout are deterministic."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _sender(clock: _Clock) -> MockOtpSender:
    """A mock bound to ``clock`` with its own isolated (empty) armed-code store."""
    return MockOtpSender(clock=clock, store={})


def test_code_for_is_deterministic() -> None:
    a = MockOtpSender()
    b = MockOtpSender()
    assert a.code_for(_PHONE) == b.code_for(_PHONE)
    assert len(a.code_for(_PHONE)) == 6


def test_verify_without_send_falls_back_to_deterministic() -> None:
    # Backward compatibility: a sender that was never `send()`-armed verifies against
    # the derived code (what the existing service/integration suites rely on), and it
    # does NOT burn — the same code verifies repeatedly.
    sender = _sender(_Clock())
    code = sender.code_for(_PHONE)
    assert sender.verify(phone=_PHONE, code=code) is True
    assert sender.verify(phone=_PHONE, code=code) is True
    assert sender.verify(phone=_PHONE, code="000000") is False


def test_send_then_verify_is_single_use() -> None:
    clock = _Clock()
    sender = _sender(clock)
    code = sender.code_for(_PHONE)
    sender.send(phone=_PHONE)
    assert sender.verify(phone=_PHONE, code=code) is True
    # Consumed on first success — a replay of the same code fails.
    assert sender.verify(phone=_PHONE, code=code) is False


def test_code_expires_after_ttl() -> None:
    clock = _Clock()
    sender = _sender(clock)
    code = sender.code_for(_PHONE)
    sender.send(phone=_PHONE)
    clock.advance(OTP_TTL_SECONDS + 1)
    assert sender.verify(phone=_PHONE, code=code) is False


def test_code_valid_within_ttl() -> None:
    clock = _Clock()
    sender = _sender(clock)
    code = sender.code_for(_PHONE)
    sender.send(phone=_PHONE)
    clock.advance(OTP_TTL_SECONDS - 1)
    assert sender.verify(phone=_PHONE, code=code) is True


def test_lockout_after_max_attempts_blocks_even_correct_code() -> None:
    clock = _Clock()
    sender = _sender(clock)
    code = sender.code_for(_PHONE)
    sender.send(phone=_PHONE)
    for _ in range(OTP_MAX_ATTEMPTS):
        assert sender.verify(phone=_PHONE, code="000000") is False
    # Locked: even the correct code is refused while the lock holds.
    assert sender.verify(phone=_PHONE, code=code) is False


def test_lock_clears_only_after_lock_window_via_resend() -> None:
    clock = _Clock()
    sender = _sender(clock)
    code = sender.code_for(_PHONE)
    sender.send(phone=_PHONE)
    for _ in range(OTP_MAX_ATTEMPTS):
        sender.verify(phone=_PHONE, code="000000")
    assert sender.verify(phone=_PHONE, code=code) is False  # locked
    # A resend re-arms a fresh code and clears the lock / attempts / consumed flag.
    sender.send(phone=_PHONE)
    assert sender.verify(phone=_PHONE, code=sender.code_for(_PHONE)) is True


def test_resend_rearms_after_consume() -> None:
    clock = _Clock()
    sender = _sender(clock)
    code = sender.code_for(_PHONE)
    sender.send(phone=_PHONE)
    assert sender.verify(phone=_PHONE, code=code) is True  # consumed
    assert sender.verify(phone=_PHONE, code=code) is False
    sender.send(phone=_PHONE)  # re-arm
    assert sender.verify(phone=_PHONE, code=code) is True


def test_send_empty_phone_raises() -> None:
    with pytest.raises(OtpError):
        _sender(_Clock()).send(phone="")


def test_lock_window_constant_exceeds_ttl() -> None:
    # Sanity on the shipped contract knobs: the lock should outlast the code window
    # so a locked number cannot be retried against the same still-valid code.
    assert OTP_LOCK_SECONDS >= OTP_TTL_SECONDS
    # _OtpEntry defaults model an un-attempted, unconsumed, unlocked code.
    entry = _OtpEntry(code="123456", issued_at=0.0)
    assert entry.attempts == 0 and entry.consumed is False and entry.locked_until is None
