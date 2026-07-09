"""Tests for cross-cutting middleware: rate-limit shape and security headers.

The in-memory limiter decision itself is covered in ``test_ratelimit``; here we pin
the middleware's rejection contract — a 429 carrying a ``Retry-After`` header so a
client backs off deterministically — and the pass-through when allowed. The
``SecurityHeadersMiddleware`` tests pin the report-only CSP rollout (ASS-278): the
header is observation-only (``Content-Security-Policy-Report-Only``), the enforcing
``Content-Security-Policy`` header is never sent, and an empty policy setting opts
the header out entirely.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, override_settings

from config.middleware import InMemoryRateLimitMiddleware, SecurityHeadersMiddleware
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


def test_security_headers_include_report_only_csp_not_enforced() -> None:
    """The CSP rollout is observation-only: report-only header present, enforcing absent."""
    middleware = SecurityHeadersMiddleware(_ok)
    response = middleware(_RF.get("/"))
    assert response["Content-Security-Policy-Report-Only"] == (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'self'; "
        "object-src 'none'"
    )
    assert "Content-Security-Policy" not in response
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response["X-Frame-Options"] == "DENY"


@override_settings(CONTENT_SECURITY_POLICY_REPORT_ONLY="")
def test_security_headers_omit_csp_when_policy_is_empty() -> None:
    """An empty policy string is an opt-out: no CSP header of either kind is sent."""
    middleware = SecurityHeadersMiddleware(_ok)
    response = middleware(_RF.get("/"))
    assert "Content-Security-Policy-Report-Only" not in response
    assert "Content-Security-Policy" not in response
