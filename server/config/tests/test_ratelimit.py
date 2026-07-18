"""Tests for the rate-limiter backend abstraction (ASS-257, ASS-268).

Covers the in-memory sliding-window behaviour, backend selection via
``RATELIMIT_BACKEND`` (including the fail-safe to in-memory when Redis is selected but
unreachable), and the real cross-worker Redis limiter. The Redis tests run against a
live Redis (localhost:6379 by default) and ``pytest.skip`` when none is reachable, so
the suite still passes on machines/CI without Redis.
"""

from __future__ import annotations

import time
import uuid

import pytest
from django.test import override_settings
from redis.exceptions import RedisError

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


@override_settings(
    RATELIMIT_BACKEND="redis",
    # Port 1 is never a Redis: the connection is refused, so the probe must degrade.
    RATELIMIT_REDIS_URL="redis://127.0.0.1:1/0",
)
def test_get_rate_limiter_redis_unreachable_fails_safe_to_memory() -> None:
    # Redis selected but unreachable: get_rate_limiter must degrade to in-memory,
    # never crash the request path — rate limiting is a guardrail, not a SPOF.
    assert isinstance(get_rate_limiter(), InMemoryRateLimiter)


@override_settings(RATELIMIT_BACKEND="something-else")
def test_get_rate_limiter_unknown_fails_safe_to_memory() -> None:
    assert isinstance(get_rate_limiter(), InMemoryRateLimiter)


def test_redis_limiter_degrades_to_in_memory_on_runtime_failure() -> None:
    # Simulate Redis dropping AFTER a healthy start (the init probe cannot catch this):
    # an unreachable Redis makes allow() hit a connection error at call time. It must
    # NOT propagate — that would 5xx every request through the middleware — so it
    # degrades to the process-local in-memory fallback, which still limits per worker.
    limiter = RedisRateLimiter(url="redis://127.0.0.1:1/0")  # connection refused
    assert limiter.allow(key="k", limit=1, window_seconds=60) is True
    assert limiter.allow(key="k", limit=1, window_seconds=60) is False  # fallback limits


# --- Live Redis backend (ASS-268) -------------------------------------------------
#
# These exercise the real cross-worker limiter. They require a reachable Redis and
# skip cleanly otherwise; each uses a unique key namespace and cleans up after itself.


def _redis_or_skip() -> RedisRateLimiter:
    """Return a connected RedisRateLimiter, or skip if no Redis is reachable."""
    limiter = RedisRateLimiter()
    try:
        limiter.check_connection()
    except (RedisError, OSError) as exc:  # connection refused / timeout / DNS
        pytest.skip(f"Redis not available for rate-limiter tests: {exc}")
    return limiter


def _cleanup(limiter: RedisRateLimiter, *keys: str) -> None:
    """Delete the namespaced sorted sets created by the given client keys."""
    client, _ = limiter._connect()
    for key in keys:
        client.delete(f"{RedisRateLimiter.KEY_PREFIX}{key}")


def test_redis_allows_exactly_limit_then_blocks() -> None:
    limiter = _redis_or_skip()
    key = f"test-{uuid.uuid4().hex}"
    try:
        # Exactly ``limit`` hits are admitted...
        for _ in range(3):
            assert limiter.allow(key=key, limit=3, window_seconds=60) is True
        # ...and the (limit + 1)th in the same window is blocked.
        assert limiter.allow(key=key, limit=3, window_seconds=60) is False
    finally:
        _cleanup(limiter, key)


def test_redis_keys_are_independent() -> None:
    limiter = _redis_or_skip()
    key_a = f"test-{uuid.uuid4().hex}"
    key_b = f"test-{uuid.uuid4().hex}"
    try:
        assert limiter.allow(key=key_a, limit=1, window_seconds=60) is True
        assert limiter.allow(key=key_a, limit=1, window_seconds=60) is False
        # A different client has its own bucket.
        assert limiter.allow(key=key_b, limit=1, window_seconds=60) is True
    finally:
        _cleanup(limiter, key_a, key_b)


def test_redis_window_expires_and_reallows() -> None:
    limiter = _redis_or_skip()
    key = f"test-{uuid.uuid4().hex}"
    try:
        assert limiter.allow(key=key, limit=1, window_seconds=1) is True
        assert limiter.allow(key=key, limit=1, window_seconds=1) is False
        # After the 1s window elapses the earlier hit ages out and a new one is allowed.
        time.sleep(1.2)
        assert limiter.allow(key=key, limit=1, window_seconds=1) is True
    finally:
        _cleanup(limiter, key)


def test_get_rate_limiter_redis_returns_redis_when_reachable() -> None:
    # Prove the wiring end to end: with Redis reachable, the redis backend is selected.
    _redis_or_skip()  # skip if no Redis
    with override_settings(RATELIMIT_BACKEND="redis"):
        assert isinstance(get_rate_limiter(), RedisRateLimiter)
