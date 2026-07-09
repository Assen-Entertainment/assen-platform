"""Rate-limiter backend abstraction for the middleware limiter (ASS-257).

The cross-cutting rate limiter (``config.middleware.InMemoryRateLimitMiddleware``)
was an inline in-memory fixed window — correct only per process, so it cannot bound
traffic across workers. This module extracts the pluggable boundary so the
production Redis-backed limiter is a drop-in swap rather than a rewrite:

- :class:`RateLimiter` — the ABC (one ``allow`` decision).
- :class:`InMemoryRateLimiter` — the default; the previous per-process fixed-window
  behaviour, unchanged.
- :class:`RedisRateLimiter` — the shared, cross-worker limiter (ASS-268). A single
  atomic Lua sliding-window per hit keeps the ``allow`` semantics identical to the
  in-memory backend while sharing state across every worker via Redis.
- :func:`get_rate_limiter` — selects the backend from ``settings.RATELIMIT_BACKEND``
  and **fails safe to in-memory** when Redis is selected but its connection cannot
  be established (the limiter must never be a single point of failure).

Alignment with the ninja throttle (config.throttle): the ninja throttles are
Django-cache-backed. Pointing both this limiter and ``CACHES`` at the same Redis
instance (when ``RATELIMIT_BACKEND=redis``) is what makes the whole surface share
one cross-worker view — a deployment concern, not wired here.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from time import monotonic, time

from django.conf import settings
from redis import Redis
from redis.commands.core import Script
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RateLimiter(ABC):
    """A sliding-window rate-limit decision, keyed by an opaque client identifier."""

    @abstractmethod
    def allow(self, *, key: str, limit: int, window_seconds: int) -> bool:
        """Return whether a request from ``key`` is within ``limit`` per window.

        Records the hit when allowed; returns ``False`` (and records nothing) once
        the window is full.
        """
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    """Per-process sliding-window limiter (default; the extracted middleware boundary).

    ``allow`` counts only the hits inside the trailing ``window_seconds`` (a sliding
    window), not calendar-aligned buckets. In-memory and per-process, so it is *not*
    correct across workers — it exists to provide a working contract and nail the
    abstraction. The real limiter shares state in Redis (see :class:`RedisRateLimiter`).
    """

    def __init__(self) -> None:
        """Initialise the per-client hit buckets."""
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, *, key: str, limit: int, window_seconds: int) -> bool:
        """Sliding-window check over the last ``window_seconds`` for ``key``."""
        now = monotonic()
        window_start = now - window_seconds
        recent = [t for t in self._hits[key] if t >= window_start]
        if len(recent) >= limit:
            self._hits[key] = recent
            return False
        recent.append(now)
        self._hits[key] = recent
        return True


class RedisRateLimiter(RateLimiter):
    """Shared, cross-worker sliding-window limiter backed by Redis (ASS-268).

    Each client key maps to a Redis sorted set whose members are individual hits
    scored by their wall-clock timestamp. ``allow`` runs one Lua script that, in a
    single atomic server-side evaluation, (1) drops members older than the trailing
    window, (2) counts what remains, and (3) records the new hit only when the count
    is under ``limit``. Because the read-decide-write is one atomic script, concurrent
    workers cannot race past the limit — the correctness the in-memory backend cannot
    provide across processes.

    The wall clock (``time``) is used rather than ``monotonic`` because scores must be
    comparable across separate workers/hosts sharing the same Redis. Keys are
    namespaced under :attr:`KEY_PREFIX` and given a TTL of one window so idle clients
    evaporate. The Redis connection is created lazily on first use and reused.
    """

    # Namespace so limiter keys never collide with other users of the same Redis DB.
    KEY_PREFIX = "assen:rl:"

    # Bound both connect and read/write so a wedged Redis fails fast (and, via
    # get_rate_limiter's probe, degrades to in-memory) instead of stalling requests.
    _SOCKET_TIMEOUT_SECONDS = 1.0

    # Atomic sliding window over a per-key sorted set. Faithful to InMemoryRateLimiter:
    # remove hits strictly older than ``now - window`` (keeping ``score >= window_start``),
    # then admit the hit only when fewer than ``limit`` remain.
    _LUA_SLIDING_WINDOW = """
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    local member = ARGV[4]
    redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', '(' .. (now - window))
    local count = redis.call('ZCARD', KEYS[1])
    if count < limit then
        redis.call('ZADD', KEYS[1], now, member)
        redis.call('EXPIRE', KEYS[1], window)
        return 1
    end
    return 0
    """

    def __init__(self, url: str | None = None) -> None:
        """Record the Redis URL; the connection itself is opened lazily on first use.

        ``url`` defaults to ``settings.RATELIMIT_REDIS_URL`` (a dedicated DB, distinct
        from Celery's broker/result DBs) so tests can point at an unreachable address.
        """
        self._url = (
            url
            if url is not None
            else str(getattr(settings, "RATELIMIT_REDIS_URL", "redis://localhost:6379/2"))
        )
        self._client: Redis | None = None
        self._script: Script | None = None
        # Process-local guardrail for a RUNTIME Redis failure (see allow()): the
        # init-time probe only proves the connection *established*, so if Redis drops
        # afterwards we degrade to per-worker limiting rather than 5xx the request
        # path. The limiter must never be a single point of failure.
        self._fallback = InMemoryRateLimiter()

    def _connect(self) -> tuple[Redis, Script]:
        """Return the (lazily created, reused) client and its registered Lua script."""
        if self._client is None or self._script is None:
            client = Redis.from_url(
                self._url,
                socket_connect_timeout=self._SOCKET_TIMEOUT_SECONDS,
                socket_timeout=self._SOCKET_TIMEOUT_SECONDS,
            )
            self._client = client
            self._script = client.register_script(self._LUA_SLIDING_WINDOW)
        return self._client, self._script

    def check_connection(self) -> None:
        """Open the connection and PING, raising on failure (used by the fail-safe probe)."""
        client, _ = self._connect()
        client.ping()

    def allow(self, *, key: str, limit: int, window_seconds: int) -> bool:
        """Atomic sliding-window check over the last ``window_seconds`` for ``key``.

        The init-time probe (:func:`get_rate_limiter`) only guards connection
        *establishment*; Redis can still drop at runtime (restart, failover, network
        blip) after a healthy start. Because this limiter sits at the top of the
        middleware stack, an uncaught Redis error here would 5xx every request until
        Redis recovered — the exact SPOF this module forbids. So a runtime Redis
        failure degrades to the process-local in-memory limiter (per-worker limiting
        continues) instead of propagating; the client is reset so a later call retries
        Redis once it is back.
        """
        try:
            client, script = self._connect()
            now = time()
            # A unique member per hit so simultaneous requests never collapse to one.
            member = f"{now!r}:{uuid.uuid4().hex}"
            allowed = script(
                keys=[f"{self.KEY_PREFIX}{key}"],
                args=[now, window_seconds, limit, member],
                client=client,
            )
            return bool(allowed)
        except (RedisError, OSError):
            logger.warning(
                "RedisRateLimiter: runtime Redis failure, degrading to in-memory",
                exc_info=True,
            )
            self._client = None
            self._script = None
            return self._fallback.allow(
                key=key, limit=limit, window_seconds=window_seconds
            )


# Registry of wired backends. ``redis`` is the shared cross-worker limiter; a
# ``RATELIMIT_BACKEND`` naming an unregistered backend still fails safe to in-memory
# via the ``.get`` default (see :func:`get_rate_limiter`).
_BACKENDS: dict[str, type[RateLimiter]] = {
    "memory": InMemoryRateLimiter,
    "redis": RedisRateLimiter,
}


def get_rate_limiter() -> RateLimiter:
    """Return the configured limiter, failing safe to in-memory.

    ``settings.RATELIMIT_BACKEND`` (default ``"memory"``) selects the backend. A
    value naming an unregistered backend resolves to :class:`InMemoryRateLimiter`
    rather than crashing the request path: the limiter must never be a single point of
    failure, and per-process limiting is strictly safer than none.

    When ``"redis"`` is selected, the connection is probed once here; if Redis is
    unreachable (connection refused/timeout/DNS) the limiter degrades to in-memory
    instead of taking down the request path. Rate limiting is a guardrail, never a SPOF.
    """
    backend = str(getattr(settings, "RATELIMIT_BACKEND", "memory")).lower()
    limiter_cls = _BACKENDS.get(backend, InMemoryRateLimiter)
    limiter = limiter_cls()
    if isinstance(limiter, RedisRateLimiter):
        try:
            limiter.check_connection()
        except (RedisError, OSError):
            return InMemoryRateLimiter()
    return limiter
