"""Rate-limiter backend abstraction for the middleware limiter (ASS-257).

The cross-cutting rate limiter (``config.middleware.InMemoryRateLimitMiddleware``)
was an inline in-memory fixed window — correct only per process, so it cannot bound
traffic across workers. This module extracts the pluggable boundary so the
production Redis-backed limiter is a drop-in swap rather than a rewrite:

- :class:`RateLimiter` — the ABC (one ``allow`` decision).
- :class:`InMemoryRateLimiter` — the default; the previous per-process fixed-window
  behaviour, unchanged.
- :class:`RedisRateLimiter` — a placeholder for the shared, cross-worker limiter;
  wiring is deployment-bound (Redis) and lands with that gate.
- :func:`get_rate_limiter` — selects the backend from ``settings.RATELIMIT_BACKEND``
  and **fails safe to in-memory** when Redis is selected but not yet wired.

Alignment with the ninja throttle (config.throttle): the ninja throttles are
Django-cache-backed. Pointing both this limiter and ``CACHES`` at the same Redis
instance (when ``RATELIMIT_BACKEND=redis``) is what makes the whole surface share
one cross-worker view — a deployment concern, not wired here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from time import monotonic

from django.conf import settings


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
    """Placeholder for the shared, cross-worker limiter (deployment-bound).

    Not wired: the Redis connection and the atomic INCR/EXPIRE window are
    deployment concerns that land with the Redis gate. Selecting it via
    ``RATELIMIT_BACKEND=redis`` today fails safe to :class:`InMemoryRateLimiter`
    (see :func:`get_rate_limiter`); a real implementation replaces this body with
    an atomic Redis fixed/sliding window keyed identically to ``allow``.
    """

    def allow(self, *, key: str, limit: int, window_seconds: int) -> bool:
        """Not implemented — Redis wiring is deployment-bound (see class docstring)."""
        raise NotImplementedError("RedisRateLimiter is not wired yet (Redis gate).")


# Registry of *wired* backends. ``redis`` is intentionally absent until the shared
# limiter lands — a ``RATELIMIT_BACKEND`` naming an unregistered backend fails safe
# to in-memory via the ``.get`` default (see :func:`get_rate_limiter`). Add the
# ``"redis": RedisRateLimiter`` entry at that point.
_BACKENDS: dict[str, type[RateLimiter]] = {
    "memory": InMemoryRateLimiter,
}


def get_rate_limiter() -> RateLimiter:
    """Return the configured limiter, failing safe to in-memory.

    ``settings.RATELIMIT_BACKEND`` (default ``"memory"``) selects the backend. A
    value naming an unregistered backend — including ``"redis"`` until it is wired —
    resolves to :class:`InMemoryRateLimiter` rather than crashing the request path:
    the limiter must never be a single point of failure, and per-process limiting is
    strictly safer than none while Redis is pending.
    """
    backend = str(getattr(settings, "RATELIMIT_BACKEND", "memory")).lower()
    return _BACKENDS.get(backend, InMemoryRateLimiter)()
