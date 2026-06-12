"""Cross-cutting HTTP middleware skeletons (Technical Architecture §3.5 #1).

Only the *outer* cross-cutting concerns belong in Django middleware: request id,
security headers, and rate limiting. Auth/session, consent gate, and RBAC live at
the Ninja layer (they need the resolved route/account, not just the raw request);
idempotency lives at the command layer (§3.5 #3). This module supplies minimal,
dependency-free implementations so the ordering can be wired into settings now and
fleshed out later — the rate limiter in particular is an in-memory placeholder
because the production limiter is deployment-bound (Redis).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Callable
from time import monotonic

from django.http import HttpRequest, HttpResponse, JsonResponse

# Header carrying the per-request correlation id, echoed to the client and
# available to logs/audit so a request can be traced end to end.
REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware:
    """Attach a unique id to every request and echo it on the response.

    Placed first (§3.5 #1) so the id exists before any later concern logs. If the
    client supplied one we keep it (distributed tracing); otherwise we mint one.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Store the next handler in the chain."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Set ``request.request_id`` and mirror it onto the response header."""
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming or uuid.uuid4().hex
        request.request_id = request_id  # type: ignore[attr-defined]
        response = self.get_response(request)
        response[REQUEST_ID_HEADER] = request_id
        return response


class SecurityHeadersMiddleware:
    """Add baseline security response headers (§3.5 #1, after request id).

    Complements Django's ``SecurityMiddleware`` with a few defaults Django does
    not set by itself. Kept conservative so it is safe to enable platform-wide;
    stricter CSP is deferred to when the front-end surfaces are known.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Store the next handler in the chain."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Apply security headers to the outgoing response."""
        response = self.get_response(request)
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("X-Frame-Options", "DENY")
        return response


class InMemoryRateLimitMiddleware:
    """A naive fixed-window rate limiter (skeleton; production uses Redis).

    In-memory and per-process, so it is *not* correct across workers — it exists
    to nail the middleware position (§3.5 #1, after security headers, before the
    Ninja auth layer) and provide a working contract. The real limiter is a
    drop-in that shares state in Redis (deployment-bound, hence not wired here).
    """

    # Generous default so the placeholder never interferes with normal use/tests.
    DEFAULT_LIMIT = 1000
    WINDOW_SECONDS = 60

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Initialise the next handler and the per-client hit buckets."""
        self.get_response = get_response
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: HttpRequest) -> str:
        """Identify the client for bucketing (remote address at this layer)."""
        # request.META values are typed Any; coerce to str for a stable dict key.
        return str(request.META.get("REMOTE_ADDR", "unknown"))

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Reject the request with 429 if the per-window limit is exceeded."""
        now = monotonic()
        key = self._client_key(request)
        window_start = now - self.WINDOW_SECONDS
        recent = [t for t in self._hits[key] if t >= window_start]
        if len(recent) >= self.DEFAULT_LIMIT:
            self._hits[key] = recent
            return JsonResponse(
                {"detail": "Rate limit exceeded."}, status=429
            )
        recent.append(now)
        self._hits[key] = recent
        return self.get_response(request)
