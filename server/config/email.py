"""Email send adapter boundary + a local mock + real adapters + verification-token signing.

Mirrors ``config/otp.py`` / ``config/social_auth.py``: ships the abstract
:class:`EmailSender` boundary, a deterministic :class:`MockEmailSender` (dev/QA, logs
the message — NEVER a real send), and the two REAL adapters —
:class:`SesEmailSender` (AWS SES) and :class:`SmtpEmailSender` (generic SMTP). Which
one :func:`email_sender` returns is env-driven:

- ``ENABLE_MOCK_EMAIL`` on (dev/test/demo, hardcoded False in base/prod) → the mock,
  always winning so those environments never reach a real provider.
- ``EMAIL_SENDER_BACKEND=ses`` / ``=smtp``, FULLY configured → that real adapter.
- anything else — unset, unknown, or a PARTIAL config → ``None``, so the surface fails
  closed (503) rather than pretend a mail was delivered — the same fail-closed shape as
  ``identity_verifier`` / ``social_auth_provider``.

Seam pattern (as in ``config/payment.py``): the adapter code ships here, while the
provider setup (SES domain/identity verification + sandbox exit, or an SMTP relay
account) stays an external credential gate. Nothing changes until a deployment sets
``EMAIL_SENDER_BACKEND`` and its settings.

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
from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMessage

# Structured, PII-aware: the mock only runs in dev/test/demo (ENABLE_MOCK_EMAIL), so
# logging the address + token there is a deliberate QA affordance, not a prod leak —
# production never constructs the mock (email_sender() returns None → 503).
logger = logging.getLogger(__name__)

# Signing salt namespacing the email-verification token (distinct from the social
# state salt) so a token minted for one purpose can never validate for another.
EMAIL_VERIFY_SALT = "assen.email.verify"

# Real transports selectable via EMAIL_SENDER_BACKEND. Anything else (including the
# empty default) selects no sender at all — the surface fails closed. config.settings.prod
# refuses to boot on a value outside this tuple, so a typo cannot silently 503 forever.
SES_BACKEND = "ses"
SMTP_BACKEND = "smtp"
SUPPORTED_EMAIL_BACKENDS = (SES_BACKEND, SMTP_BACKEND)

# Subject of the fan-facing verification mail (Korean — every fan-facing string is).
VERIFY_SUBJECT = "[Assen] 이메일 인증을 완료해 주세요"


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


def verification_url(*, web_base_url: str, token: str) -> str:
    """Build the fan-facing verify link the mail body carries.

    Points at the web app's ``/verify-email`` route (which reads ``?token=``), not the
    API — the fan lands on a page, which then calls the confirm endpoint. The token is
    query-encoded so its signing separators survive the round trip.
    """
    return f"{web_base_url.rstrip('/')}/verify-email?{urlencode({'token': token})}"


def render_verification(*, web_base_url: str, token: str) -> tuple[str, str]:
    """Return the ``(subject, plain-text body)`` of the Korean verification mail.

    Shared by both real adapters so SES and SMTP deliver an identical message. Plain
    text only: it renders everywhere, carries no tracking/remote content, and keeps the
    link inspectable before a fan clicks it.
    """
    link = verification_url(web_base_url=web_base_url, token=token)
    # The TTL is authoritative in EMAIL_VERIFY_TTL_SECONDS (load_verification_token
    # enforces it); the copy derives from it so the two can never disagree.
    hours = max(1, settings.EMAIL_VERIFY_TTL_SECONDS // 3600)
    body = (
        "안녕하세요, Assen입니다.\n\n"
        "아래 링크를 눌러 이메일 인증을 완료해 주세요.\n\n"
        f"{link}\n\n"
        f"이 링크는 {hours}시간 동안만 유효해요.\n"
        "본인이 요청하지 않았다면 이 메일을 무시해 주세요.\n"
    )
    return VERIFY_SUBJECT, body


def _reply_to_addresses() -> list[str]:
    """Return the verification mail's Reply-To list, or ``[]`` when it is unset.

    Optional by design: ``EMAIL_REPLY_TO_ADDRESS`` empty (the default) yields no
    Reply-To header — unchanged behavior — while a set value (normalized with
    ``.strip()`` exactly like ``from_email`` in :func:`email_sender`) routes replies to a
    real inbox instead of the no-reply From: box. Shared by both real senders so SES and
    SMTP add the same header, or omit it identically — an empty setting must never become
    a stray ``[""]``.
    """
    reply_to = settings.EMAIL_REPLY_TO_ADDRESS.strip()
    return [reply_to] if reply_to else []


def _log_verification_sent(event: str, email: str) -> None:
    """Log a delivery event carrying NO PII and NO token.

    Unlike :class:`MockEmailSender` (dev/test/demo only, where logging the address +
    token is a deliberate QA affordance), the real senders run in production: the token
    is a bearer credential — anyone reading it could complete the verification — and the
    address is raw PII. Only the domain is recorded, which is enough to spot a failing
    provider without identifying the fan.
    """
    logger.info(event, extra={"email_domain": email.rpartition("@")[2]})


class SmtpEmailSender(EmailSender):
    """Real SMTP adapter — delivers the verification mail via Django's mail stack.

    Goes through :mod:`django.core.mail` (the configured ``EMAIL_BACKEND``, Django's
    SMTP backend by default) rather than hand-rolled :mod:`smtplib`, so host/port/TLS/
    timeout/credentials all come from the standard ``EMAIL_*`` settings and the suite
    can capture sends through the locmem backend. Selected by
    ``EMAIL_SENDER_BACKEND=smtp``, and only when fully configured (:func:`email_sender`).
    """

    def __init__(self, *, from_email: str, web_base_url: str) -> None:
        """Bind the From: address + the web origin the verify link points at."""
        self._from_email = from_email
        self._web_base_url = web_base_url

    def send_verification(self, *, email: str, token: str) -> None:
        """Send the Korean verification mail over SMTP; raise on delivery failure."""
        subject, body = render_verification(
            web_base_url=self._web_base_url, token=token
        )
        # reply_to only when configured: _reply_to_addresses() is [] when unset, which
        # Django treats as "no Reply-To" (identical to omitting it) — never a stray [""].
        message = EmailMessage(
            subject=subject,
            body=body,
            from_email=self._from_email,
            to=[email],
            reply_to=_reply_to_addresses(),
        )
        try:
            # fail_silently=False is Django's default; it is explicit here because a
            # swallowed failure would report a verification mail that never left.
            message.send(fail_silently=False)
        except OSError as exc:
            # smtplib.SMTPException and ssl.SSLError are both OSError subclasses, so
            # this covers refused/failed relays and socket/TLS errors alike.
            raise EmailSendError(f"SMTP verification send failed: {exc}") from exc
        _log_verification_sent("email.smtp.verification_sent", email)


def _build_ses_client(region: str) -> Any:
    """Construct the boto3 SESv2 client for ``region``.

    Import-lazy so boto3 loads only when SES is actually selected, and isolated in a
    module function so tests can stub the client without touching boto3 itself.
    Credentials are NEVER passed: boto3 resolves them from the ambient AWS chain (the
    ECS task role), so no static access key exists to leak or rotate.
    """
    import boto3

    return boto3.client("sesv2", region_name=region)


class SesEmailSender(EmailSender):
    """Real AWS SES adapter — SESv2 ``send_email`` through boto3.

    Transport choice (SES API over SES's SMTP interface): the API signs with the ambient
    ECS task role, whereas SES-over-SMTP needs a dedicated long-lived IAM SMTP
    credential pair in the environment — a static secret to ship, store, and rotate. The
    API also surfaces per-send errors (MessageRejected, sandbox/verification failures)
    as typed botocore exceptions instead of SMTP status codes. boto3 is already a
    dependency (django-storages[s3]), so this adds nothing to the lockfile. Selected by
    ``EMAIL_SENDER_BACKEND=ses``, and only when fully configured (:func:`email_sender`).
    """

    def __init__(self, *, region: str, from_email: str, web_base_url: str) -> None:
        """Bind the SES region, the (SES-verified) From: address, and the web origin."""
        self._region = region
        self._from_email = from_email
        self._web_base_url = web_base_url
        self._client: Any | None = None

    def send_verification(self, *, email: str, token: str) -> None:
        """Send the Korean verification mail via SES; raise on any SES/transport error."""
        subject, body = render_verification(
            web_base_url=self._web_base_url, token=token
        )
        send_kwargs: dict[str, Any] = {
            "FromEmailAddress": self._from_email,
            "Destination": {"ToAddresses": [email]},
            "Content": {
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                }
            },
        }
        # ReplyToAddresses is a top-level SESv2 send_email argument; include it only when
        # configured so an unset Reply-To leaves the key off entirely (no empty list).
        reply_to = _reply_to_addresses()
        if reply_to:
            send_kwargs["ReplyToAddresses"] = reply_to
        try:
            self._ses_client().send_email(**send_kwargs)
        except Exception as exc:
            # Broad by intent: botocore raises ClientError/BotoCoreError (and their many
            # subclasses) plus credential-resolution errors. Every one of them means the
            # mail did NOT go out, so all of them must reach the caller — never a silent
            # success. Chained (`from exc`) so the original SES error stays diagnosable.
            raise EmailSendError(f"SES verification send failed: {exc}") from exc
        _log_verification_sent("email.ses.verification_sent", email)

    def _ses_client(self) -> Any:
        """Return the SESv2 client, building it on first use (clients are reusable)."""
        if self._client is None:
            self._client = _build_ses_client(self._region)
        return self._client


def email_sender() -> EmailSender | None:
    """Return the configured email sender, or ``None`` when none is fully wired.

    Precedence — the mock always wins where it is enabled, so dev/test/demo can never
    reach a real provider even with real settings present:

    - ``ENABLE_MOCK_EMAIL`` (dev/test/demo; hardcoded False in base/prod) →
      :class:`MockEmailSender`, whose no-op "send" can never back a real verification.
    - ``EMAIL_SENDER_BACKEND=ses`` → :class:`SesEmailSender`, iff the SES region, the
      From: address, and the web base URL are all set.
    - ``EMAIL_SENDER_BACKEND=smtp`` → :class:`SmtpEmailSender`, iff ``EMAIL_HOST``, the
      From: address, and the web base URL are all set.
    - anything else — unset, unknown, or a PARTIALLY configured backend → ``None``.

    Fail-closed by construction: a half-configured backend yields ``None`` (the surface
    503s) rather than a sender that would raise on every signup, so "email is off" and
    "email is broken" stay distinguishable — mirroring ``social_auth_provider`` /
    ``identity_verifier``. The web base URL counts as required config because without it
    no usable verify link can be built.
    """
    if settings.ENABLE_MOCK_EMAIL:
        return MockEmailSender()

    backend: str = settings.EMAIL_SENDER_BACKEND.strip().lower()
    from_email: str = settings.EMAIL_FROM_ADDRESS.strip()
    web_base_url: str = settings.WEB_BASE_URL.strip()
    if not backend or not from_email or not web_base_url:
        return None

    if backend == SES_BACKEND:
        region: str = settings.EMAIL_SES_REGION.strip()
        if not region:
            return None
        return SesEmailSender(
            region=region, from_email=from_email, web_base_url=web_base_url
        )
    if backend == SMTP_BACKEND:
        if not settings.EMAIL_HOST.strip():
            return None
        return SmtpEmailSender(from_email=from_email, web_base_url=web_base_url)
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
