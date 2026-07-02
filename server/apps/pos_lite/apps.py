"""App configuration for the pos_lite domain."""

from __future__ import annotations

from django.apps import AppConfig


class PosLiteConfig(AppConfig):
    """Configures the pos_lite app (POS Lite manual order linking, ASS-102 v0)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pos_lite"
