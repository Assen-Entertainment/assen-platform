"""Test settings: in-memory sqlite + eager Celery so the suite needs no servers.

This keeps `pytest` and `makemigrations --check` runnable in CI and locally
without a Postgres or Redis instance (the smoke tests touch neither a real DB
nor the broker).
"""

from __future__ import annotations

import tempfile

from config.settings.base import *  # noqa: F403

# Uploaded media goes to a throwaway temp dir so the suite never writes into the
# repo tree (and each machine/run gets an isolated, disposable location).
MEDIA_ROOT = tempfile.mkdtemp(prefix="assen-test-media-")

# Enable local media serving so the upload endpoint is active in the suite (the
# fail-closed 503 path is asserted explicitly via override_settings).
SERVE_LOCAL_MEDIA = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# Run tasks synchronously in-process; no broker required.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Fast, deterministic password hashing for tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Fan signup tests + live API E2E use the deterministic mock OTP sender.
ENABLE_MOCK_FAN_OTP = True

# R3 gated features on for tests: the mock KYC verifier + mock payment tokenizer are
# wired, and 19+ read exposure is on so the gating tests can assert both the
# hidden-when-off and shown-when-verified paths. All mock/skeleton (see base.py); the
# off-by-default (base) behaviour is asserted explicitly with override_settings.
ENABLE_MOCK_KYC = True
ENABLE_ADULT_CONTENT = True
ENABLE_MOCK_PAYMENT = True
# Exercise the (privacy-gated) delivery checkout in fixtures; base/prod/demo keep
# it hardcoded False (ASS-287 A-1).
ENABLE_SHIPPING_CHECKOUT = True

# Disable per-user write throttling: the suite fires many writes for one fixture
# account, and the shared LocMem throttle cache would otherwise leak state across
# tests and trip 429s. Throttle behaviour itself is exercised in dev/prod config.
FAN_WRITE_THROTTLE_ENABLED = False
