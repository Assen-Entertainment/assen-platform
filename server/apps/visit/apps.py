"""App configuration for the visit domain."""

from __future__ import annotations

from django.apps import AppConfig


class VisitConfig(AppConfig):
    """Configures the visit app (VisitRecord + the QR CheckinToken, ASS-94/99)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.visit"
