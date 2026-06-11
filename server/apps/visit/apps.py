"""App configuration for the visit domain."""

from __future__ import annotations

from django.apps import AppConfig


class VisitConfig(AppConfig):
    """Configures the visit app. Models arrive in P4/P5 (empty in P0)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.visit"
