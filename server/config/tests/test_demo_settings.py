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
