"""Social login (OAuth2) adapter boundary + a local mock.

Mirrors ``config/identity_verify.py`` and ``config/otp.py``: this ships only the
abstract :class:`SocialAuthProvider` boundary and a deterministic mock, so the
social-login flow (카카오/Google/Naver) can be built and QA'd end-to-end without a
real OAuth app or any provider round-trip.

A real provider (Kakao REST / Google / Naver OAuth2) is a separate **credential
gate**; when wired it replaces :class:`MockSocialAuthProvider` behind this same
boundary, exchanging the authorization code for a provider token out of band and
returning the same minimal :class:`SocialProfile`. Only the provider + an opaque
``subject`` (and a display nickname) ever cross this boundary or persist — the
account is keyed on a namespaced HMAC of ``provider:subject``
(:func:`apps.identity.social_services.hash_social`), never the raw provider token.

Lives in ``config/`` (infrastructure, no model coupling at runtime), mirroring
``config/otp.py`` and ``config/identity_verify.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlencode

from django.conf import settings

# Social providers this surface accepts (대표 결정 2026-07-14: 카카오·Google·Naver).
# A real adapter maps each to its OAuth2 authorize/token endpoints; unknown providers
# are rejected at the API boundary (SOCIAL_PROVIDER_UNSUPPORTED).
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

    Two steps mirror a real OAuth handshake: :meth:`authorize_url` builds the provider
    consent URL the client is redirected to, and :meth:`exchange` turns the
    authorization ``code`` the provider returns into a :class:`SocialProfile`. A real
    adapter verifies the code with the provider out of band and never lets the raw
    provider token cross this boundary.

    TODO (real providers — credential gate): production adapters delegate to Kakao
    REST / Google / Naver OAuth2 (client id/secret from Secrets Manager), verify the
    token, and map the provider's user id to ``SocialProfile.subject``.
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
    ``redirect_uri`` with a deterministic mock code (so the flow completes on our
    origin, with no external provider), and :meth:`exchange` returns one stable mock
    user per provider (repeated logins reuse a single account). Not for production: a
    real adapter delegates to the provider's OAuth2 endpoints.
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


def social_auth_provider() -> SocialAuthProvider | None:
    """Return the configured social auth provider, or ``None`` when none is wired.

    The deterministic mock is gated behind ``ENABLE_MOCK_SOCIAL_AUTH`` (off in
    production) so its unverifiable identities can never back a real login. With no
    real provider wired yet, production returns ``None`` and the social surface fails
    closed (503) — mirroring :func:`config.identity_verify.identity_verifier` and
    ``_otp_sender``.
    """
    if settings.ENABLE_MOCK_SOCIAL_AUTH:
        return MockSocialAuthProvider()
    return None
