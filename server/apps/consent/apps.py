"""App configuration for the consent domain."""

from __future__ import annotations

from django.apps import AppConfig


class ConsentConfig(AppConfig):
    """Configures the consent app (P4 foundation: consent records + gate)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.consent"
