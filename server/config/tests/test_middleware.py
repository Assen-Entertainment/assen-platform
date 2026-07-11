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

import re

from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, override_settings

from config.middleware import (
    REQUEST_ID_HEADER,
    InMemoryRateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from config.ratelimit import RateLimiter

_RF = RequestFactory()

# A server-minted id is uuid4 hex: 32 lowercase hex chars, nothing else.
_MINTED_ID_RE = re.compile(r"^[0-9a-f]{32}$")


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


# --- request-id trust boundary (ASS-291 #7) ---------------------------------- #


def test_request_id_honours_a_well_formed_client_id() -> None:
    """A client id matching the opaque grammar is kept for distributed tracing."""
    middleware = RequestIDMiddleware(_ok)
    request = _RF.get("/", HTTP_X_REQUEST_ID="trace-abc_123.45")
    response = middleware(request)
    assert response[REQUEST_ID_HEADER] == "trace-abc_123.45"
    assert getattr(request, "request_id") == "trace-abc_123.45"  # noqa: B009 - dynamic attr


def test_request_id_mints_a_fresh_id_when_absent() -> None:
    """With no client header a fresh server id (uuid4 hex) is minted."""
    response = RequestIDMiddleware(_ok)(_RF.get("/"))
    assert _MINTED_ID_RE.match(response[REQUEST_ID_HEADER])


def test_request_id_rejects_injected_client_id_and_mints_fresh() -> None:
    """A malformed X-Request-ID (log-forging CRLF + PII) is discarded, not echoed.

    An attacker-supplied id carrying a newline and a phone number must never reach
    the response header or the log stream; the middleware mints a clean server id
    instead, so no injected content survives.
    """
    injected = "abc\r\nSet-Cookie: x=1 010-1234-5678"
    response = RequestIDMiddleware(_ok)(_RF.get("/", HTTP_X_REQUEST_ID=injected))
    echoed = response[REQUEST_ID_HEADER]
    assert echoed != injected
    assert "\n" not in echoed and "\r" not in echoed and " " not in echoed
    assert "010-1234-5678" not in echoed
    assert _MINTED_ID_RE.match(echoed)  # fell back to a minted id


def test_request_id_rejects_overlong_client_id() -> None:
    """An over-long id (past the 64-char bound) is discarded for a fresh server id."""
    response = RequestIDMiddleware(_ok)(_RF.get("/", HTTP_X_REQUEST_ID="a" * 65))
    assert _MINTED_ID_RE.match(response[REQUEST_ID_HEADER])
