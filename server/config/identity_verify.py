"""Identity verification (KYC / 성인 19+ 인증) adapter boundary + a local mock (R3).

Mirrors ``config/otp.py``: this ships only the abstract :class:`IdentityVerifier`
boundary and a deterministic mock, so the 본인인증 flow can be built and tested
without a real provider or storing any PII.

법무 경계 (R3 계획 법무 경계 정본): the boundary NEVER receives 주민번호/CI/DI/생년월일
원본 — a method takes only the already-authenticated
:class:`~apps.identity.models.Account` and returns a *derived* adult flag. A real
provider (NICE/PASS/KCB/아이핀) is a separate 대표·법무 gate; when wired it replaces
:class:`MockIdentityVerifier` behind this same boundary, exchanging provider-side
tokens out of band, and only the derived ``adult_verified`` / ``kyc_status`` ever
persist (Account fields) — never the source identity document.

HUMAN-REVIEW-REQUIRED: auth/identity (CONSTRAINTS #26).

Lives in ``config/`` (infrastructure, no model coupling at runtime), mirroring
``config/otp.py`` and ``config/storage.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from apps.identity.models import Account


class IdentityVerificationError(Exception):
    """Raised when an identity verification cannot be started or confirmed."""


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of a confirmed verification — a *derived* result only.

    ``adult`` is the sole fact the platform keeps (19+ gating). No 생년월일/이름/
    주민번호 is carried here or stored anywhere; a real provider returns the same
    minimal boolean across this boundary.
    """

    adult: bool


@dataclass(frozen=True)
class VerificationChallenge:
    """Provider handshake params a client needs to complete 본인인증.

    A real adapter fills these (the provider session id + the redirect / SDK
    entry the client is sent to); the client returns to
    :meth:`IdentityVerifier.confirm` afterwards with the provider token. The mock
    has no provider, so :meth:`IdentityVerifier.start` returns ``None`` and the
    client is confirmed directly. Carries NO PII — only opaque handshake refs.
    """

    provider: str
    redirect_url: str
    session_id: str


class IdentityVerifier(ABC):
    """Boundary for 본인인증 (KYC / 성인 인증).

    Two steps mirror a real 본인인증 handshake: :meth:`start` kicks off a challenge
    (a real adapter would redirect to / call the provider) and :meth:`confirm`
    resolves it to a :class:`VerificationResult`. Crucially neither method takes any
    PII — the caller passes only the already-authenticated
    :class:`~apps.identity.models.Account`, and a real adapter exchanges provider
    tokens out of band, so the source 주민번호/CI/DI never enters this process or the
    database.

    TODO (real provider — HUMAN-REVIEW-REQUIRED, 대표·법무 gate): a production adapter
    delegates to NICE/PASS/KCB/아이핀, verifies the provider signature, and maps the
    provider's 성인 여부 to ``VerificationResult.adult`` — persisting only that
    derived flag, never the underlying identity document.
    """

    @abstractmethod
    def start(self, *, account: Account) -> VerificationChallenge | None:
        """Begin a verification challenge for ``account``; raise on failure.

        Returns the provider handshake params the client must act on (a real
        adapter → redirect/SDK), or ``None`` when there is no provider step to
        arrange (the mock, which is confirmed directly).
        """
        raise NotImplementedError

    @abstractmethod
    def confirm(
        self, *, account: Account, token: str | None = None
    ) -> VerificationResult:
        """Resolve the challenge to a :class:`VerificationResult`; raise on failure.

        ``token`` is the provider's post-cert verification reference (imp_uid /
        verification id) the client returns after completing 본인인증; a real
        adapter verifies it with the provider. The mock ignores it — there is no
        provider to verify, and the source 주민번호/CI/DI never enters here.
        """
        raise NotImplementedError


class MockIdentityVerifier(IdentityVerifier):
    """Deterministic local verifier for dev/tests — no real 본인인증, no PII.

    :meth:`start` is a no-op (there is no provider to call) and :meth:`confirm`
    deterministically returns an adult result, so the verify flow can be exercised
    end-to-end. Not for production: a real adapter delegates to a 본인인증 provider and
    returns the provider's actual 성인 여부. No input carries PII (mirrors
    :class:`~config.otp.MockOtpSender`, which never stores the phone number).
    """

    def start(self, *, account: Account) -> VerificationChallenge | None:
        """No-op start: there is no provider challenge to arrange in the mock."""
        del account
        return None

    def confirm(
        self, *, account: Account, token: str | None = None
    ) -> VerificationResult:
        """Return a deterministic adult result (mock passes; no PII, no token)."""
        del account, token
        return VerificationResult(adult=True)


def identity_verifier() -> IdentityVerifier | None:
    """Return the configured identity verifier, or ``None`` when none is wired.

    The deterministic mock is gated behind ``ENABLE_MOCK_KYC`` (off in production) so
    its unconditional pass can never back a real 성인/본인 인증. With no real provider
    wired yet, production returns ``None`` and the verify surface fails closed (503)
    rather than trust an unverifiable result — mirroring ``_otp_sender`` in
    :mod:`apps.identity.api`.
    """
    if settings.ENABLE_MOCK_KYC:
        return MockIdentityVerifier()
    return None
