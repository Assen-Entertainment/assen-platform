"""Ninja authentication for opaque access tokens (ADR-0002).

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26).

``OpaqueTokenAuth`` is the custom ``HttpBearer`` that turns a ``Authorization:
Bearer <token>`` header into the calling :class:`Account`, or denies the request.
It is the single server-side gate where access tokens are validated, so instant
revocation (F11) is honoured on every authenticated call.
"""

from __future__ import annotations

from django.http import HttpRequest
from ninja.security import HttpBearer

from apps.identity.models import Account
from apps.identity.services import TokenError, verify_access_token


class OpaqueTokenAuth(HttpBearer):
    """Resolve a bearer access token to an Account, attaching it to the request.

    Returning the account (truthy) authorises the request; returning ``None``
    makes Ninja respond 401. The resolved account is stashed on
    ``request.auth`` by Ninja and additionally on ``request.account`` for the
    RBAC permission helpers to read.
    """

    def authenticate(self, request: HttpRequest, token: str) -> Account | None:
        """Validate the token; return the Account or None on any failure."""
        try:
            account = verify_access_token(token)
        except TokenError:
            return None
        # Expose the principal for downstream RBAC guards (admin_rbac.permissions).
        request.account = account  # type: ignore[attr-defined]
        return account
