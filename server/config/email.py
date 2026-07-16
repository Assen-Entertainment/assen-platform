"""Email send adapter boundary + a local mock + the verification-token signing.

Mirrors ``config/otp.py`` / ``config/social_auth.py``: ships the abstract
:class:`EmailSender` boundary and a deterministic :class:`MockEmailSender` (dev/QA,
logs the message — NEVER a real send), so the email + password fan-auth flow can be
built and tested without an SMTP account. Which one :func:`email_sender` returns is
env-driven: the mock only when ``ENABLE_MOCK_EMAIL`` is on (dev/test/demo), else
``None`` so the surface fails closed (503) rather than pretend a mail was delivered —
the same fail-closed shape as ``_otp_sender`` / ``social_auth_provider``.

The verification token is a :func:`django.core.signing.dumps` payload
(``{"account_id", "email"}``) under a dedicated salt with a TTL
(``EMAIL_VERIFY_TTL_SECONDS``), reusing the signed-state pattern of the social OAuth
work — it needs no server-side store (cross-worker safe) and cannot be forged without
``SECRET_KEY``. For dev QA the mock logs the token AND the signup response echoes it
when ``EMAIL_VERIFY_RETURN_TOKEN`` is on (dev/test only), so e2e can complete the
confirm step without a real inbox.

Lives in ``config/`` (infrastructure, no model coupling at runtime), mirroring
``config/otp.py`` and ``config/storage.py``.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from django.conf import settings
from django.core import signing

# Structured, PII-aware: the mock only runs in dev/test/demo (ENABLE_MOCK_EMAIL), so
# logging the address + token there is a deliberate QA affordance, not a prod leak —
# production never constructs the mock (email_sender() returns None → 503).
logger = logging.getLogger(__name__)

# Signing salt namespacing the email-verification token (distinct from the social
# state salt) so a token minted for one purpose can never validate for another.
EMAIL_VERIFY_SALT = "assen.email.verify"


class EmailSendError(Exception):
    """Raised when an email cannot be sent."""


class EmailSender(ABC):
    """Boundary for sending fan-facing transactional email.

    Only the verification mail is modelled today; a real adapter (SES/SMTP) replaces
    the mock behind :func:`email_sender` without touching call sites. No inbound path
    and no stored message body — the sender is send-only.
    """

    @abstractmethod
    def send_verification(self, *, email: str, token: str) -> None:
        """Send (or arrange) the email-verification link for ``email``.

        ``token`` is the signed :func:`make_verification_token` value the confirm
        endpoint unsigns. Raise :class:`EmailSendError` on delivery failure.
        """
        raise NotImplementedError


class MockEmailSender(EmailSender):
    """Deterministic local sender for dev/tests — logs the message, no real send.

    Not for production: it delivers nothing (anyone reading the log could complete a
    verification), so it is gated behind ``ENABLE_MOCK_EMAIL`` and paired with
    ``EMAIL_VERIFY_RETURN_TOKEN`` (dev/test) so the confirm flow stays completable
    without an inbox. A real adapter delegates to an email provider.
    """

    def send_verification(self, *, email: str, token: str) -> None:
        """Log the verification mail (address + token) instead of sending it."""
        logger.info(
            "email.mock.verification_sent",
            extra={"email": email, "token": token},
        )


def email_sender() -> EmailSender | None:
    """Return the configured email sender, or ``None`` when none is wired.

    The deterministic mock is gated behind ``ENABLE_MOCK_EMAIL`` (off in production)
    so its no-op "send" can never back a real verification. With no real email adapter
    wired yet, production returns ``None`` and the email-auth surface fails closed
    (503) — mirroring ``_otp_sender`` / ``identity_verifier`` / ``social_auth_provider``.
    """
    if settings.ENABLE_MOCK_EMAIL:
        return MockEmailSender()
    return None


def make_verification_token(*, account_id: int, email: str) -> str:
    """Mint the signed email-verification token for an account + address.

    Binds the token to both the account id and the email so a token cannot be replayed
    against a different account or after the address changed. Unforgeable without
    ``SECRET_KEY`` and self-expiring via :func:`load_verification_token`'s ``max_age``.
    """
    return signing.dumps(
        {"account_id": account_id, "email": email}, salt=EMAIL_VERIFY_SALT
    )


def load_verification_token(token: str) -> tuple[int, str]:
    """Unsign a verification token to ``(account_id, email)`` within its TTL.

    Raises :class:`django.core.signing.BadSignature` (incl. ``SignatureExpired``) on a
    forged/expired token, and on a structurally invalid payload — so the caller can
    treat every bad-token case as one 400 without inspecting the shape.
    """
    payload = signing.loads(
        token, salt=EMAIL_VERIFY_SALT, max_age=settings.EMAIL_VERIFY_TTL_SECONDS
    )
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("account_id"), int)
        or not isinstance(payload.get("email"), str)
    ):
        raise signing.BadSignature("Malformed email verification token payload.")
    return payload["account_id"], payload["email"]
