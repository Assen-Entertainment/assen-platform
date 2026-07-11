"""Smoke test: the DEMO profile turns every mock gate ON atop prod hardening.

The demo settings inherit prod (fail-closed on required env), so the test supplies
the required env vars and imports the module fresh, then asserts all four mock
flags are True and DEBUG stayed off (it is a hardened profile, not a dev one).
"""

from __future__ import annotations

import importlib
import sys

import pytest


def test_demo_profile_enables_all_mock_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    # demo → prod fail-closes on these; provide them so the import succeeds.
    monkeypatch.setenv("DJANGO_SECRET_KEY", "demo-smoke-secret-not-real")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "demo.example")
    # prod also fail-closes on the data/broker stores (ASS-265) — a demo host runs
    # on a real Postgres/Redis, so these are required too.
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@localhost:5432/demo")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    # prod also requires the dedicated phone-identifier HMAC key (ASS-287 A-2).
    monkeypatch.setenv(
        "PHONE_IDENTIFIER_HMAC_KEY", "demo-smoke-phone-hmac-key-not-real-0123456789"
    )
    # Evaluate demo (and its prod parent) fresh under the env set above.
    for module in ("config.settings.demo", "config.settings.prod"):
        sys.modules.pop(module, None)
    demo = importlib.import_module("config.settings.demo")

    assert demo.ENABLE_MOCK_FAN_OTP is True
    assert demo.ENABLE_MOCK_KYC is True
    assert demo.ENABLE_MOCK_PAYMENT is True
    assert demo.ENABLE_ADULT_CONTENT is True
    # Inherits prod hardening — never a debug/dev profile.
    assert demo.DEBUG is False
