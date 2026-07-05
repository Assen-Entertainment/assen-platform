"""Tests for the rate-limiter backend abstraction (ASS-257).

Covers the in-memory fixed-window behaviour, backend selection via
``RATELIMIT_BACKEND`` (including the fail-safe to in-memory when Redis is selected
but unwired), and that the Redis placeholder is honestly unimplemented.
"""

from __future__ import annotations

import pytest
from django.test import override_settings

from config.ratelimit import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    get_rate_limiter,
)


def test_in_memory_allows_up_to_limit_then_blocks() -> None:
    limiter = InMemoryRateLimiter()
    for _ in range(3):
        assert limiter.allow(key="ip-1", limit=3, window_seconds=60) is True
    # Fourth hit in the same window is blocked.
    assert limiter.allow(key="ip-1", limit=3, window_seconds=60) is False


def test_in_memory_keys_are_independent() -> None:
    limiter = InMemoryRateLimiter()
    assert limiter.allow(key="a", limit=1, window_seconds=60) is True
    assert limiter.allow(key="a", limit=1, window_seconds=60) is False
    # A different client has its own bucket.
    assert limiter.allow(key="b", limit=1, window_seconds=60) is True


def test_in_memory_window_slides(monkeypatch: pytest.MonkeyPatch) -> None:
    now = {"t": 1000.0}
    monkeypatch.setattr("config.ratelimit.monotonic", lambda: now["t"])
    limiter = InMemoryRateLimiter()
    assert limiter.allow(key="ip", limit=1, window_seconds=60) is True
    assert limiter.allow(key="ip", limit=1, window_seconds=60) is False
    # Advance past the window: the earlier hit ages out and a new one is allowed.
    now["t"] += 61
    assert limiter.allow(key="ip", limit=1, window_seconds=60) is True


@override_settings(RATELIMIT_BACKEND="memory")
def test_get_rate_limiter_memory() -> None:
    assert isinstance(get_rate_limiter(), InMemoryRateLimiter)


@override_settings(RATELIMIT_BACKEND="redis")
def test_get_rate_limiter_redis_fails_safe_to_memory() -> None:
    # Redis is not wired yet: selecting it must degrade to in-memory, never crash.
    assert isinstance(get_rate_limiter(), InMemoryRateLimiter)


@override_settings(RATELIMIT_BACKEND="something-else")
def test_get_rate_limiter_unknown_fails_safe_to_memory() -> None:
    assert isinstance(get_rate_limiter(), InMemoryRateLimiter)


def test_redis_limiter_is_not_wired() -> None:
    with pytest.raises(NotImplementedError):
        RedisRateLimiter().allow(key="ip", limit=1, window_seconds=60)
