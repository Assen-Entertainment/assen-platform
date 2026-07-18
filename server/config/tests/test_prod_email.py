"""Production boot contract for the email transport (config.email seam).

Deliberately NOT symmetric with the rate-limiter checks next door: prod must still boot
with NO email configured (the endpoint 503s instead, like the payment/KYC gates), so a
deployment without SES/SMTP credentials keeps serving reads + social login. The one
case that fails closed LOUDLY is an *unknown* backend name — it can never select an
adapter, so email signup would 503 forever while the env looks configured.
"""

from __future__ import annotations

import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured


def _base_prod_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The other prod-required env so the import reaches the email check."""
    monkeypatch.setenv("DJANGO_SECRET_KEY", "prod-smoke-secret-not-real")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "prod.example")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@localhost:5432/prod")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    monkeypatch.setenv(
        "PHONE_IDENTIFIER_HMAC_KEY", "prod-smoke-phone-hmac-key-not-real-0123456789"
    )
    monkeypatch.setenv("RATELIMIT_BACKEND", "redis")
    monkeypatch.setenv("RATELIMIT_REDIS_URL", "redis://localhost:6379/2")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")


def _import_prod() -> object:
    """Re-import config.settings.prod, so its module-level checks run against the env.

    Only `prod` is evicted (as in test_prod_ratelimit): the already-imported
    `config.settings.base` stays cached, so values prod star-imports from base keep the
    value base computed at ITS first import — which is why these tests assert on the
    import SUCCEEDING/RAISING, not on env-derived settings attributes. prod's own checks
    re-read env() at import time, so they do see the monkeypatched environment (the same
    reason the ASS-295 rate-limit checks are written that way).
    """
    sys.modules.pop("config.settings.prod", None)
    return importlib.import_module("config.settings.prod")


def test_prod_boots_without_any_email_config(monkeypatch: pytest.MonkeyPatch) -> None:
    # The 503 seam, not a boot-fail: no email creds must not take the whole API down —
    # reads and social login keep serving.
    _base_prod_env(monkeypatch)
    monkeypatch.delenv("EMAIL_SENDER_BACKEND", raising=False)
    prod = _import_prod()
    assert prod.DEBUG is False  # type: ignore[attr-defined]
    # ...and the log-only mock can never be what fills that gap in prod (base hardcodes
    # it False, so no env var can flip it — this attribute is NOT env-derived).
    assert prod.ENABLE_MOCK_EMAIL is False  # type: ignore[attr-defined]


def test_prod_boots_with_a_partially_configured_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Valid-but-incomplete stays a runtime 503 (config.email.email_sender() → None),
    # consistent with the payment/KYC gates — the API still boots and serves.
    _base_prod_env(monkeypatch)
    monkeypatch.setenv("EMAIL_SENDER_BACKEND", "ses")
    monkeypatch.delenv("EMAIL_FROM_ADDRESS", raising=False)
    monkeypatch.delenv("WEB_BASE_URL", raising=False)
    prod = _import_prod()
    assert prod.DEBUG is False  # type: ignore[attr-defined]


@pytest.mark.parametrize("backend", ["ses", "smtp", " SES "])
def test_prod_boots_with_a_supported_backend(
    monkeypatch: pytest.MonkeyPatch, backend: str
) -> None:
    _base_prod_env(monkeypatch)
    monkeypatch.setenv("EMAIL_SENDER_BACKEND", backend)
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "no-reply@assen.example")
    monkeypatch.setenv("WEB_BASE_URL", "https://assen.example")
    monkeypatch.setenv("EMAIL_HOST", "smtp.example")
    prod = _import_prod()
    assert prod.DEBUG is False  # type: ignore[attr-defined]


@pytest.mark.parametrize("backend", ["sendgrid", "smpt", "SES-v2"])
def test_prod_refuses_an_unknown_email_backend(
    monkeypatch: pytest.MonkeyPatch, backend: str
) -> None:
    # A typo'd/unsupported name can never select an adapter — fail at boot rather than
    # 503 silently forever while the env looks configured.
    _base_prod_env(monkeypatch)
    monkeypatch.setenv("EMAIL_SENDER_BACKEND", backend)
    with pytest.raises(ImproperlyConfigured, match="EMAIL_SENDER_BACKEND"):
        _import_prod()
