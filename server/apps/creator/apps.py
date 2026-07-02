"""App configuration for the creator domain (SDLC 09 §3, E11/B1)."""

from __future__ import annotations

from django.apps import AppConfig


class CreatorConfig(AppConfig):
    """Configures the creator app — creator profiles for the new platform."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.creator"
