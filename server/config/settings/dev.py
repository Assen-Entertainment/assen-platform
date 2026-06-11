"""Development settings: DEBUG on, eager-friendly Celery, local hosts."""

from __future__ import annotations

from config.settings.base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
