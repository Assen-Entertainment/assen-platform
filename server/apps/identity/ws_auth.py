"""WebSocket authentication middleware for the realtime surface (ASS-240).

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26).

The app authenticates with opaque access tokens (ADR-0002), not Django's session
auth, so Channels' ``AuthMiddlewareStack`` does not fit. This middleware resolves
the same fan access token the HTTP surface uses — the ``Authorization: Bearer``
header (app/native clients) or the httpOnly ``assen_access`` cookie (the browser
WebSocket, which cannot set custom headers) — through the *single* server-side
gate :func:`apps.identity.services.verify_access_token`, so instant revocation
(F11) is honoured on the socket exactly as on REST. The resolved account is
injected as ``scope["account"]`` (``None`` when unauthenticated); the consumer
decides how to reject. The token is never logged.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from http.cookies import CookieError, SimpleCookie
from typing import Any

from channels.db import database_sync_to_async

from apps.identity.cookies import ACCESS_COOKIE_NAME
from apps.identity.models import Account
from apps.identity.services import TokenError, verify_access_token

# Minimal ASGI type aliases (Channels ships no stubs; these keep our own code
# strict-typed at the boundary).
Scope = MutableMapping[str, Any]
ASGIReceive = Callable[[], Awaitable[MutableMapping[str, Any]]]
ASGISend = Callable[[MutableMapping[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, ASGIReceive, ASGISend], Awaitable[None]]


def _token_from_scope(scope: Scope) -> str | None:
    """Extract the presented fan access token from an ASGI WebSocket scope.

    Mirrors the HTTP gate's precedence (:func:`apps.identity.auth.access_token_from_request`):
    the ``Authorization: Bearer`` header first, then the ``assen_access`` cookie.
    The raw header/cookie bytes are decoded as latin-1 (the ASGI byte-string
    convention). Never logs the token.
    """
    headers: dict[bytes, bytes] = dict(scope.get("headers") or [])
    authorization = headers.get(b"authorization", b"").decode("latin1")
    if authorization.startswith("Bearer "):
        token = authorization[len("Bearer ") :].strip()
        if token:
            return token
    cookie_header = headers.get(b"cookie", b"").decode("latin1")
    if cookie_header:
        jar: SimpleCookie = SimpleCookie()
        try:
            jar.load(cookie_header)
        except CookieError:
            return None
        morsel = jar.get(ACCESS_COOKIE_NAME)
        if morsel is not None and morsel.value:
            return morsel.value
    return None


def _resolve_account_sync(token: str) -> Account | None:
    """Resolve a token to its account via the shared fan gate, or ``None``.

    Delegates to :func:`apps.identity.services.verify_access_token` (the one gate)
    so revocation/expiry take effect on the socket immediately; a rejected token
    yields ``None`` rather than raising.
    """
    try:
        return verify_access_token(token)
    except TokenError:
        return None


class FanAuthMiddleware:
    """ASGI middleware injecting ``scope["account"]`` for WebSocket connections.

    Wraps the inner ASGI app (typically a :class:`channels.routing.URLRouter`).
    Resolves the fan account off the presented bearer token / access cookie and
    stashes it (or ``None``) on a fresh copy of the scope before delegating, so a
    consumer can authorise the connection without re-implementing the gate.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap the inner ASGI application."""
        self.app = app

    async def __call__(self, scope: Scope, receive: ASGIReceive, send: ASGISend) -> None:
        """Resolve the account into a fresh scope, then delegate to the inner app."""
        token = _token_from_scope(scope)
        account = await database_sync_to_async(_resolve_account_sync)(token) if token else None
        scope = dict(scope)
        scope["account"] = account
        await self.app(scope, receive, send)
