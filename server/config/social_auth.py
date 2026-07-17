"""Social login (OAuth2) adapter boundary + a local mock + real provider adapters.

Mirrors ``config/identity_verify.py`` and ``config/otp.py``: ships the abstract
:class:`SocialAuthProvider` boundary, a deterministic :class:`MockSocialAuthProvider`
(dev/QA, no provider round-trip), and :class:`RealSocialAuthProvider` (카카오/Google/
Naver OAuth2). Which one :func:`social_auth_provider` returns is env-driven:

- Real credentials configured (``SOCIAL_{PROVIDER}_CLIENT_ID`` + ``_CLIENT_SECRET``) →
  the real adapter handles that provider (and the mock, when ``ENABLE_MOCK_SOCIAL_AUTH``
  is on, still covers any provider without real creds — e.g. dev over http).
- No real creds + ``ENABLE_MOCK_SOCIAL_AUTH`` → pure mock.
- Neither → ``None`` (surface fails closed, 503).

Only the provider + an opaque ``subject`` (and a display nickname) cross this boundary
or persist — the account is keyed on a namespaced HMAC of ``provider:subject``
(:func:`apps.identity.social_services.hash_social`), never the raw provider token.

Lives in ``config/`` (infrastructure, no model coupling at runtime).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from django.conf import settings

# Social providers this surface accepts (대표 결정 2026-07-14: 카카오·Google·Naver).
SUPPORTED_SOCIAL_PROVIDERS = ("kakao", "google", "naver")


class SocialAuthError(Exception):
    """Raised when a social authorization cannot be started or exchanged."""


@dataclass(frozen=True)
class SocialProfile:
    """The minimal identity a provider returns after a successful OAuth exchange.

    ``subject`` is the provider's stable per-user id (opaque); ``display_name`` is a
    convenience nickname (may be ``None``). No email / real name / provider access
    token is carried across this boundary or stored — the account is keyed on a
    namespaced HMAC of ``provider:subject``.
    """

    provider: str
    subject: str
    display_name: str | None = None


class SocialAuthProvider(ABC):
    """Boundary for social login (OAuth2 authorization-code flow).

    :meth:`authorize_url` builds the provider consent URL the client is redirected to;
    :meth:`exchange` turns the authorization ``code`` the provider returns into a
    :class:`SocialProfile`.
    """

    @abstractmethod
    def authorize_url(self, *, provider: str, state: str, redirect_uri: str) -> str:
        """Return the provider consent URL to redirect the client to."""
        raise NotImplementedError

    @abstractmethod
    def exchange(
        self, *, provider: str, code: str, redirect_uri: str
    ) -> SocialProfile:
        """Exchange the authorization ``code`` for a profile; raise on failure."""
        raise NotImplementedError


class MockSocialAuthProvider(SocialAuthProvider):
    """Deterministic local social provider for dev/tests — no real OAuth, no PII.

    :meth:`authorize_url` sends the browser straight back to the caller's own
    ``redirect_uri`` with a deterministic mock code (the flow completes on our origin,
    with no external provider), and :meth:`exchange` returns one stable mock user per
    provider (repeated logins reuse a single account).
    """

    def authorize_url(self, *, provider: str, state: str, redirect_uri: str) -> str:
        """Bounce back to ``redirect_uri`` with a mock code — no external provider."""
        sep = "&" if "?" in redirect_uri else "?"
        query = urlencode(
            {"provider": provider, "code": f"mock-{provider}", "state": state}
        )
        return f"{redirect_uri}{sep}{query}"

    def exchange(
        self, *, provider: str, code: str, redirect_uri: str
    ) -> SocialProfile:
        """Return one deterministic mock user per provider (no real identity)."""
        del code, redirect_uri
        return SocialProfile(
            provider=provider,
            subject=f"mock-{provider}-user",
            display_name=f"{provider} 테스트",
        )


@dataclass(frozen=True)
class _ProviderEndpoints:
    """OAuth2 endpoints + default scope for a real provider."""

    authorize: str
    token: str
    userinfo: str
    scope: str


_ENDPOINTS: dict[str, _ProviderEndpoints] = {
    "kakao": _ProviderEndpoints(
        authorize="https://kauth.kakao.com/oauth/authorize",
        token="https://kauth.kakao.com/oauth/token",
        userinfo="https://kapi.kakao.com/v2/user/me",
        scope="profile_nickname",
    ),
    "google": _ProviderEndpoints(
        authorize="https://accounts.google.com/o/oauth2/v2/auth",
        token="https://oauth2.googleapis.com/token",
        userinfo="https://openidconnect.googleapis.com/v1/userinfo",
        scope="openid email profile",
    ),
    "naver": _ProviderEndpoints(
        authorize="https://nid.naver.com/oauth2.0/authorize",
        token="https://nid.naver.com/oauth2.0/token",
        userinfo="https://openapi.naver.com/v1/nid/me",
        scope="",
    ),
}


def _post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    """POST an ``application/x-www-form-urlencoded`` body and parse the JSON reply."""
    body = urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return _read_json(request)


def _get_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    """GET a JSON resource with the given headers (e.g. a Bearer token)."""
    return _read_json(urllib.request.Request(url, method="GET", headers=headers))


def _read_json(request: urllib.request.Request) -> dict[str, Any]:
    """Execute ``request`` (10s timeout) and return the JSON object, or raise."""
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            payload = response.read().decode("utf-8")
    except urllib.error.URLError as exc:  # includes HTTPError (non-2xx)
        raise SocialAuthError(f"provider request failed: {exc}") from exc
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SocialAuthError("provider returned non-JSON payload") from exc
    if not isinstance(parsed, dict):
        raise SocialAuthError("provider returned an unexpected payload")
    return parsed


class RealSocialAuthProvider(SocialAuthProvider):
    """카카오/Google/Naver OAuth2 adapter (authorization-code flow).

    ``credentials`` maps each configured provider to its ``(client_id, client_secret)``.
    A provider without credentials falls through to ``fallback`` (the mock, when
    enabled) or raises — so a partial configuration is explicit, never silent.
    """

    def __init__(
        self,
        credentials: dict[str, tuple[str, str]],
        *,
        fallback: SocialAuthProvider | None = None,
    ) -> None:
        """Bind per-provider credentials + an optional fallback for unconfigured ones."""
        self._credentials = credentials
        self._fallback = fallback

    def authorize_url(self, *, provider: str, state: str, redirect_uri: str) -> str:
        """Build the provider's OAuth2 consent URL (or defer to the fallback)."""
        creds = self._credentials.get(provider)
        if creds is None:
            return self._defer("authorize_url", provider).authorize_url(
                provider=provider, state=state, redirect_uri=redirect_uri
            )
        client_id, _secret = creds
        endpoints = _ENDPOINTS[provider]
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        if endpoints.scope:
            params["scope"] = endpoints.scope
        return f"{endpoints.authorize}?{urlencode(params)}"

    def exchange(
        self, *, provider: str, code: str, redirect_uri: str
    ) -> SocialProfile:
        """Exchange ``code`` for a token, read the profile, and normalise it."""
        creds = self._credentials.get(provider)
        if creds is None:
            return self._defer("exchange", provider).exchange(
                provider=provider, code=code, redirect_uri=redirect_uri
            )
        client_id, client_secret = creds
        endpoints = _ENDPOINTS[provider]
        token = _post_form(
            endpoints.token,
            {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        access_token = token.get("access_token")
        if not access_token:
            raise SocialAuthError(f"{provider} token exchange returned no token.")
        info = _get_json(
            endpoints.userinfo, {"Authorization": f"Bearer {access_token}"}
        )
        return _map_profile(provider, info)

    def _defer(self, op: str, provider: str) -> SocialAuthProvider:
        """Return the fallback for an unconfigured provider, or raise."""
        if self._fallback is not None:
            return self._fallback
        raise SocialAuthError(f"social provider '{provider}' is not configured.")


def _map_profile(provider: str, info: dict[str, Any]) -> SocialProfile:
    """Normalise a provider's userinfo payload into a :class:`SocialProfile`."""
    if provider == "kakao":
        subject = str(info.get("id") or "")
        profile = (info.get("kakao_account") or {}).get("profile") or {}
        name = profile.get("nickname") or (info.get("properties") or {}).get("nickname")
    elif provider == "google":
        subject = str(info.get("sub") or "")
        name = info.get("name")
    elif provider == "naver":
        response = info.get("response") or {}
        subject = str(response.get("id") or "")
        name = response.get("nickname") or response.get("name")
    else:  # pragma: no cover - guarded by _require_supported_provider upstream
        subject, name = "", None
    if not subject:
        raise SocialAuthError(f"{provider} did not return a stable user id.")
    return SocialProfile(provider=provider, subject=subject, display_name=name)


def _configured_credentials() -> dict[str, tuple[str, str]]:
    """Collect the providers with BOTH a client id and secret set in settings."""
    creds: dict[str, tuple[str, str]] = {}
    for provider in SUPPORTED_SOCIAL_PROVIDERS:
        prefix = f"SOCIAL_{provider.upper()}"
        client_id = getattr(settings, f"{prefix}_CLIENT_ID", "")
        client_secret = getattr(settings, f"{prefix}_CLIENT_SECRET", "")
        if client_id and client_secret:
            creds[provider] = (client_id, client_secret)
    return creds


def social_auth_provider() -> SocialAuthProvider | None:
    """Return the configured social auth provider, or ``None`` when none is wired.

    Real per-provider credentials win where present; the deterministic mock (gated by
    ``ENABLE_MOCK_SOCIAL_AUTH``, off in production) covers the rest. With neither, the
    social surface fails closed (503) — mirroring ``identity_verifier`` / ``email_sender``.
    """
    creds = _configured_credentials()
    fallback = MockSocialAuthProvider() if settings.ENABLE_MOCK_SOCIAL_AUTH else None
    if creds:
        return RealSocialAuthProvider(creds, fallback=fallback)
    return fallback
