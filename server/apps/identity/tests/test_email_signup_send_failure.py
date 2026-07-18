"""Email signup when the sender is wired but the send FAILS (coded 503, not 500).

``signup_email`` already fails closed with a coded 503 when *no* sender is configured.
A configured-but-broken sender (refused SMTP relay, SES error → ``EmailSendError``) is
the same thing from the caller's side — email is not available right now — but it used
to escape as an uncoded 500: no ``code`` for the web to branch on, a Sentry page for a
provider outage, and a non-retryable-looking status for a transient condition.

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client

from config.email import EmailSendError

pytestmark = pytest.mark.django_db

_EMAIL = "send-fails@example.com"


def _signup(client: Client) -> Any:
    return client.post(
        "/api/fan/signup/email",
        data=json.dumps(
            {
                "email": _EMAIL,
                "password": "correct horse 8",
                "nickname": "발송실패",
                "consent_terms": True,
                "consent_privacy": True,
                "age_over_14": True,
            }
        ),
        content_type="application/json",
    )


class _BrokenSender:
    """A wired sender whose delivery always fails, like a refused relay."""

    def send_verification(self, *, email: str, token: str) -> None:
        del email, token
        raise EmailSendError("relay refused")


def test_send_failure_is_a_coded_503(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    # Patched where it is *used*, not where it is defined — apps.identity.api imported
    # the name, so patching config.email would not affect the endpoint's lookup.
    monkeypatch.setattr("apps.identity.api.email_sender", lambda: _BrokenSender())

    res = _signup(client)

    assert res.status_code == 503
    assert res.json()["code"] == "EmailUnavailable"


def test_send_failure_does_not_leak_the_provider_error(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The 503 is the fan-facing seam: the underlying relay/SES message stays in the
    # traceback (chained `from exc`) for Sentry, never in the response body.
    monkeypatch.setattr("apps.identity.api.email_sender", lambda: _BrokenSender())

    body = _signup(client).json()

    assert "relay refused" not in json.dumps(body, ensure_ascii=False)
