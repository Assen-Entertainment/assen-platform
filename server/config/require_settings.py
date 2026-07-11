"""Fail closed when ``DJANGO_SETTINGS_MODULE`` is not set explicitly (ASS-285).

The ASGI / WSGI / Celery entrypoints used to do
``os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")`` — so a
deployment that forgot to set the settings module booted **dev**: DEBUG on, every
mock gate (OTP / KYC / payment / adult / media) on, and prod's required-secret
checks never run. A single missing deploy variable silently turned the whole mock
skeleton on in production.

We refuse to default. Every entrypoint must name its settings module explicitly
(the container image sets ``config.settings.prod``; docker-compose / e2e / local
set theirs), and a missing value fails loudly here instead of shipping dev.
"""

from __future__ import annotations

import os


def require_settings_module() -> None:
    """Raise unless ``DJANGO_SETTINGS_MODULE`` is set — no silent dev fallback."""
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        raise RuntimeError(
            "DJANGO_SETTINGS_MODULE must be set explicitly — there is no dev "
            "fallback (ASS-285). Deployments set config.settings.prod; "
            "docker-compose / e2e / local dev set theirs."
        )
