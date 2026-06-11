"""App configuration for the consent domain."""

from __future__ import annotations

from django.apps import AppConfig


class ConsentConfig(AppConfig):
    """Configures the consent app. Models arrive in P4/P5 (empty in P0)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.consent"
