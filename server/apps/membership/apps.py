"""App configuration for the membership domain (SDLC 09 §3, E11/B1)."""

from __future__ import annotations

from django.apps import AppConfig


class MembershipConfig(AppConfig):
    """Configures the membership app — tier catalog (read side)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.membership"
