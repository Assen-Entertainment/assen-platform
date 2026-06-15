"""Test settings: in-memory sqlite + eager Celery so the suite needs no servers.

This keeps `pytest` and `makemigrations --check` runnable in CI and locally
without a Postgres or Redis instance (the smoke tests touch neither a real DB
nor the broker).
"""

from __future__ import annotations

from config.settings.base import *  # noqa: F403

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
