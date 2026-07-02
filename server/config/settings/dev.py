"""Development settings: DEBUG on, eager-friendly Celery, local hosts."""

from __future__ import annotations

from config.settings.base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Fan signup uses the deterministic mock OTP locally (no SMS provider wired).
ENABLE_MOCK_FAN_OTP = True

# Local web dev server origins (Next.js) — override via env when ports differ.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://127.0.0.1:3000"],
)
