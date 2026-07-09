"""Ninja authentication for opaque access tokens (ADR-0002).

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26).

This module is the single server-side gate where fan access tokens are validated,
so instant revocation (F11) is honoured on every authenticated call. Two surfaces
are supported (ADR-0002):

- ``FanBearerAuth`` — the app surface: ``Authorization: Bearer <access token>``.
- ``FanCookieAuth`` — the web surface: the httpOnly ``assen_access`` cookie.

``fan_auth`` combines them so an endpoint accepts either. ``OpaqueTokenAuth`` is a
backward-compatible alias of ``FanBearerAuth`` (the original bearer gate name used
by the check-in / RBAC surfaces). ``resolve_optional_account`` is the silent,
non-raising variant used to personalise otherwise-anonymous reads.
"""

from __future__ import annotations

from typing import Protocol, cast

from django.http import HttpRequest
from ninja.security import APIKeyCookie, HttpBearer

from apps.identity.cookies import ACCESS_COOKIE_NAME
from apps.identity.models import Account
from apps.identity.services import TokenError, verify_access_token


class AuthedHttpRequest(Protocol):
    """A request that has passed ``fan_auth`` / ``RoleRequired``.

    Ninja stashes the resolved :class:`Account` on ``request.auth`` (the auth
    class's return value), and the auth classes here mirror it onto
    ``request.account`` for the RBAC/consent helpers. Neither attribute exists on
    the base :class:`~django.http.HttpRequest`, so this Protocol is the typed view
    of an authenticated request — it lets :func:`authed` (and the ``request.account``
    writers) read/write those attributes without a per-call
    ``# type: ignore[attr-defined]``.
    """

    auth: Account
    account: Account


def authed(request: HttpRequest) -> Account:
    """Return the :class:`Account` the auth layer resolved onto ``request``.

    The single typed accessor for handlers behind an ``auth=`` gate (``fan_auth``,
    ``RoleRequired`` and friends): it replaces the repeated
    ``cast(Account, request.auth)  # type: ignore[attr-defined]`` idiom with one
    precisely-typed call. Only call it from a route that carries such a gate —
    Ninja guarantees ``request.auth`` is the :class:`Account` there.
    """
    return cast(AuthedHttpRequest, request).auth


def _authenticate(request: HttpRequest, token: str) -> Account | None:
    """Resolve a token to its account (shared by both auth surfaces).

    Returning the account (truthy) authorises the request; returning ``None``
    makes Ninja respond 401. The resolved account is stashed on ``request.account``
    for the RBAC permission helpers to read (``admin_rbac.permissions``).
    """
    try:
        account = verify_access_token(token)
    except TokenError:
        return None
    cast(AuthedHttpRequest, request).account = account
    return account


class FanBearerAuth(HttpBearer):
    """App surface: authenticate ``Authorization: Bearer <access token>``."""

    def authenticate(self, request: HttpRequest, token: str) -> Account | None:
        """Return the account for a valid bearer token, else None (→ 401)."""
        return _authenticate(request, token)


# Backward-compatible alias. ``OpaqueTokenAuth`` was the original bearer gate name
# (check-in, RBAC); it is the same gate as ``FanBearerAuth``, so keeping the alias
# lets existing imports/usages resolve unchanged after this consolidation.
OpaqueTokenAuth = FanBearerAuth


class FanCookieAuth(APIKeyCookie):
    """Web surface: authenticate the httpOnly ``assen_access`` cookie."""

    param_name = ACCESS_COOKIE_NAME

    def authenticate(self, request: HttpRequest, key: str | None) -> Account | None:
        """Return the account for a valid access cookie, else None (→ 401)."""
        if not key:
            return None
        return _authenticate(request, key)


# Role-agnostic authentication for the fan surface: try the app bearer token
# first, then the web access cookie. Either one proves the caller owns the token;
# the fan endpoints return only the caller's own data, so no staff role is
# required (role gating, where needed, is done in the handler).
fan_auth = [FanBearerAuth(), FanCookieAuth()]


def access_token_from_request(request: HttpRequest) -> str | None:
    """Extract the presented access token: bearer header first, then access cookie.

    Used where the plaintext token itself is needed (e.g. logout, which must
    revoke the token family behind the presented token). Never logs the value.
    """
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        token = header[len("Bearer ") :].strip()
        if token:
            return token
    cookie = request.COOKIES.get(ACCESS_COOKIE_NAME)
    if cookie:
        return cookie
    return None


def resolve_optional_account(request: HttpRequest) -> Account | None:
    """Best-effort authentication for optional-auth reads (bearer → cookie).

    Silently returns ``None`` on any failure (no token, expired, revoked) rather
    than raising 401, so an anonymous caller still gets the public read while an
    authenticated one gets their personalised flags (following/liked). This is the
    read-side counterpart to :data:`fan_auth`, which hard-gates writes.
    """
    token = access_token_from_request(request)
    if token is None:
        return None
    try:
        return verify_access_token(token)
    except TokenError:
        return None
