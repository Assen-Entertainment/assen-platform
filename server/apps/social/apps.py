"""App configuration for the social domain (SDLC 09 §3, E11/B1)."""

from __future__ import annotations

from django.apps import AppConfig


class SocialConfig(AppConfig):
    """Configures the social app — follow / block relations."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.social"
