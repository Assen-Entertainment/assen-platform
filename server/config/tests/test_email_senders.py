"""Backend selection + real-adapter delivery contract for :mod:`config.email`.

The email + password fan surface fails closed (503) unless ``email_sender()`` returns a
sender, so email signup being *available* and being *correct* are both settings-driven.
These lock:

- the selection matrix — mock precedence, ses/smtp only when FULLY configured, and
  ``None`` on an unset, unknown, or PARTIAL config (a half-working sender must never
  reach a fan);
- what the real adapters actually do — a Korean mail carrying the verify link, a send
  failure raised rather than swallowed, and a log line that leaks neither the bearer
  token nor the fan's address.
"""

from __future__ import annotations

import logging
from smtplib import SMTPException
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from botocore.exceptions import ClientError
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.test import override_settings

from config.email import (
    VERIFY_SUBJECT,
    EmailSendError,
    MockEmailSender,
    SesEmailSender,
    SmtpEmailSender,
    email_sender,
)

_EMAIL = "fan@example.com"
# Shaped like a real django.core.signing token (":"-separated) so the link building is
# exercised against separators that must survive query encoding.
_TOKEN = "eyJhY2NvdW50X2lkIjoxfQ:1uXyZa:signature-part_0123"
_FROM = "no-reply@assen.example"
_WEB = "https://assen.example"
_LOCMEM = "django.core.mail.backends.locmem.EmailBackend"

# A fully configured deployment of each real backend (mock explicitly off, as in prod).
_SES: dict[str, object] = {
    "ENABLE_MOCK_EMAIL": False,
    "EMAIL_SENDER_BACKEND": "ses",
    "EMAIL_FROM_ADDRESS": _FROM,
    "WEB_BASE_URL": _WEB,
    "EMAIL_SES_REGION": "ap-northeast-2",
}
_SMTP: dict[str, object] = {
    "ENABLE_MOCK_EMAIL": False,
    "EMAIL_SENDER_BACKEND": "smtp",
    "EMAIL_FROM_ADDRESS": _FROM,
    "WEB_BASE_URL": _WEB,
    "EMAIL_HOST": "smtp.example",
}


class BrokenBackend(BaseEmailBackend):
    """An ``EMAIL_BACKEND`` that fails the way a refused relay does.

    ``smtplib.SMTPException`` subclasses ``OSError`` — which is exactly the assumption
    :class:`~config.email.SmtpEmailSender` documents when it catches ``OSError``, so
    this doubles as a check on that claim. Public (not ``_``-prefixed) because Django
    resolves ``EMAIL_BACKEND`` by import path.
    """

    def send_messages(self, email_messages: Any) -> int:
        raise SMTPException("relay refused the message")


class _StubSesClient:
    """Stands in for the boto3 SESv2 client: records calls, or raises ``error``."""

    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._error = error

    def send_email(self, **kwargs: Any) -> dict[str, str]:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return {"MessageId": "stub-message-id"}


def _stub_ses(monkeypatch: pytest.MonkeyPatch, stub: _StubSesClient) -> None:
    """Route SesEmailSender at ``stub`` instead of constructing a real boto3 client."""
    monkeypatch.setattr("config.email._build_ses_client", lambda region: stub)


def _verify_link(body: str) -> str:
    """Pull the verification URL out of the mail body (it sits on its own line)."""
    return next(line for line in body.splitlines() if line.startswith(_WEB))


# --- selection matrix ---------------------------------------------------------


def test_mock_wins_even_when_a_real_backend_is_fully_configured() -> None:
    # Precedence guard: dev/test/demo must never reach a real provider, whatever else
    # the env carries. This is also what keeps the existing suite/E2E on the mock.
    with override_settings(**{**_SES, "ENABLE_MOCK_EMAIL": True}):
        assert isinstance(email_sender(), MockEmailSender)


@override_settings(**_SES)
def test_ses_selected_when_fully_configured() -> None:
    assert isinstance(email_sender(), SesEmailSender)


@override_settings(**_SMTP)
def test_smtp_selected_when_fully_configured() -> None:
    assert isinstance(email_sender(), SmtpEmailSender)


@override_settings(ENABLE_MOCK_EMAIL=False, EMAIL_SENDER_BACKEND="")
def test_none_when_backend_unset() -> None:
    # The base/prod default: no mock, no backend → the surface 503s.
    assert email_sender() is None


@override_settings(**{**_SES, "EMAIL_SENDER_BACKEND": "sendgrid"})
def test_none_when_backend_unknown() -> None:
    # An unsupported name selects nothing rather than falling back to some default.
    assert email_sender() is None


@override_settings(**{**_SES, "EMAIL_SENDER_BACKEND": " SES "})
def test_backend_name_is_normalised() -> None:
    # Whitespace/case from an env var must not silently disable email.
    assert isinstance(email_sender(), SesEmailSender)


@pytest.mark.parametrize(
    "missing", ["EMAIL_FROM_ADDRESS", "WEB_BASE_URL", "EMAIL_SES_REGION"]
)
def test_ses_partial_config_fails_closed(missing: str) -> None:
    # Every required key is load-bearing: drop any one and SES must not be selected —
    # None (503 "email is off"), never a sender that raises on every signup.
    with override_settings(**{**_SES, missing: ""}):
        assert email_sender() is None


@pytest.mark.parametrize("missing", ["EMAIL_FROM_ADDRESS", "WEB_BASE_URL", "EMAIL_HOST"])
def test_smtp_partial_config_fails_closed(missing: str) -> None:
    with override_settings(**{**_SMTP, missing: ""}):
        assert email_sender() is None


# --- SMTP adapter -------------------------------------------------------------


@override_settings(**_SMTP, EMAIL_BACKEND=_LOCMEM)
def test_smtp_sender_delivers_korean_mail_with_verify_link() -> None:
    SmtpEmailSender(from_email=_FROM, web_base_url=_WEB).send_verification(
        email=_EMAIL, token=_TOKEN
    )

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [_EMAIL]
    assert message.from_email == _FROM
    assert message.subject == VERIFY_SUBJECT
    assert "이메일 인증" in message.subject
    assert "인증을 완료해 주세요" in message.body
    # The link must be usable by the web /verify-email page: right path, and a token
    # that survives query encoding intact.
    link = _verify_link(str(message.body))
    assert link.startswith(f"{_WEB}/verify-email?token=")
    assert parse_qs(urlparse(link).query)["token"] == [_TOKEN]


@override_settings(**_SMTP, EMAIL_BACKEND=_LOCMEM)
def test_smtp_sender_trims_trailing_slash_in_base_url() -> None:
    SmtpEmailSender(from_email=_FROM, web_base_url=f"{_WEB}/").send_verification(
        email=_EMAIL, token=_TOKEN
    )
    assert _verify_link(str(mail.outbox[0].body)).startswith(f"{_WEB}/verify-email?")


@override_settings(**_SMTP, EMAIL_BACKEND="config.tests.test_email_senders.BrokenBackend")
def test_smtp_send_failure_is_not_swallowed() -> None:
    # A refused relay must reach the caller as EmailSendError — reporting
    # "verification_sent" for a mail that never left would strand the fan forever.
    with pytest.raises(EmailSendError):
        SmtpEmailSender(from_email=_FROM, web_base_url=_WEB).send_verification(
            email=_EMAIL, token=_TOKEN
        )
    assert mail.outbox == []


# --- SES adapter --------------------------------------------------------------


@override_settings(**_SES)
def test_ses_sender_calls_sesv2_send_email(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubSesClient()
    _stub_ses(monkeypatch, stub)

    SesEmailSender(
        region="ap-northeast-2", from_email=_FROM, web_base_url=_WEB
    ).send_verification(email=_EMAIL, token=_TOKEN)

    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["FromEmailAddress"] == _FROM
    assert call["Destination"] == {"ToAddresses": [_EMAIL]}
    simple = call["Content"]["Simple"]
    # Korean subject/body must be sent as UTF-8, else SES delivers mojibake.
    assert simple["Subject"] == {"Data": VERIFY_SUBJECT, "Charset": "UTF-8"}
    text = simple["Body"]["Text"]
    assert text["Charset"] == "UTF-8"
    assert "인증을 완료해 주세요" in text["Data"]
    assert parse_qs(urlparse(_verify_link(text["Data"])).query)["token"] == [_TOKEN]


@override_settings(**_SES)
def test_ses_client_is_built_once_per_sender(monkeypatch: pytest.MonkeyPatch) -> None:
    builds: list[str] = []
    stub = _StubSesClient()

    def _build(region: str) -> _StubSesClient:
        builds.append(region)
        return stub

    monkeypatch.setattr("config.email._build_ses_client", _build)
    sender = SesEmailSender(region="ap-northeast-2", from_email=_FROM, web_base_url=_WEB)
    sender.send_verification(email=_EMAIL, token=_TOKEN)
    sender.send_verification(email=_EMAIL, token=_TOKEN)

    assert builds == ["ap-northeast-2"]  # cached, and built with the configured region


@override_settings(**_SES)
def test_ses_send_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    # MessageRejected is the real sandbox/unverified-identity failure: it must surface,
    # not be swallowed into a silent success.
    boto_error = ClientError(
        {"Error": {"Code": "MessageRejected", "Message": "Email address is not verified."}},
        "SendEmail",
    )
    _stub_ses(monkeypatch, _StubSesClient(error=boto_error))

    with pytest.raises(EmailSendError) as excinfo:
        SesEmailSender(
            region="ap-northeast-2", from_email=_FROM, web_base_url=_WEB
        ).send_verification(email=_EMAIL, token=_TOKEN)
    # Chained, so the original SES error stays diagnosable in the traceback/Sentry.
    assert excinfo.value.__cause__ is boto_error


# --- PII safety ---------------------------------------------------------------


@override_settings(**_SMTP, EMAIL_BACKEND=_LOCMEM)
def test_smtp_log_carries_neither_token_nor_address(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # MockEmailSender logs both by design (dev/test/demo QA affordance); the REAL
    # senders run in production, where the token is a bearer credential and the address
    # is raw PII. Only the domain may be recorded.
    with caplog.at_level(logging.INFO, logger="config.email"):
        SmtpEmailSender(from_email=_FROM, web_base_url=_WEB).send_verification(
            email=_EMAIL, token=_TOKEN
        )

    records = [r for r in caplog.records if r.name == "config.email"]
    assert [r.getMessage() for r in records] == ["email.smtp.verification_sent"]
    # str(__dict__) covers the message AND every `extra` field the formatter can emit.
    assert _TOKEN not in str(records[0].__dict__)
    assert _EMAIL not in str(records[0].__dict__)
    assert records[0].__dict__["email_domain"] == "example.com"


@override_settings(**_SES)
def test_ses_log_carries_neither_token_nor_address(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _stub_ses(monkeypatch, _StubSesClient())

    with caplog.at_level(logging.INFO, logger="config.email"):
        SesEmailSender(
            region="ap-northeast-2", from_email=_FROM, web_base_url=_WEB
        ).send_verification(email=_EMAIL, token=_TOKEN)

    records = [r for r in caplog.records if r.name == "config.email"]
    assert [r.getMessage() for r in records] == ["email.ses.verification_sent"]
    assert _TOKEN not in str(records[0].__dict__)
    assert _EMAIL not in str(records[0].__dict__)
    assert records[0].__dict__["email_domain"] == "example.com"
