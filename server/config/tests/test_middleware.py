"""Tests for the cross-cutting rate-limit middleware 429 shape (R5-W1A).

The in-memory limiter decision itself is covered in ``test_ratelimit``; here we pin
the middleware's rejection contract — a 429 carrying a ``Retry-After`` header so a
client backs off deterministically — and the pass-through when allowed.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from config.middleware import InMemoryRateLimitMiddleware
from config.ratelimit import RateLimiter

_RF = RequestFactory()


def _ok(request: HttpRequest) -> HttpResponse:
    """Downstream handler stub."""
    return HttpResponse("ok")


class _DenyLimiter(RateLimiter):
    """A limiter that always rejects, to force the 429 branch."""

    def allow(self, *, key: str, limit: int, window_seconds: int) -> bool:
        """Reject every request."""
        return False


def test_rate_limited_429_carries_retry_after() -> None:
    middleware = InMemoryRateLimitMiddleware(_ok)
    middleware._limiter = _DenyLimiter()
    response = middleware(_RF.get("/"))
    assert response.status_code == 429
    assert response["Retry-After"] == str(middleware.WINDOW_SECONDS)


def test_request_within_limit_passes_through() -> None:
    middleware = InMemoryRateLimitMiddleware(_ok)
    response = middleware(_RF.get("/"))
    assert response.status_code == 200
