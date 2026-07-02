"""App configuration for the content domain (SDLC 09 §3, E11/B1)."""

from __future__ import annotations

from django.apps import AppConfig


class ContentConfig(AppConfig):
    """Configures the content app — posts, comments, likes."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.content"
