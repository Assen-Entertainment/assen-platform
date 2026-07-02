"""App configuration for the commerce domain (SDLC 09 §3, E11/B1)."""

from __future__ import annotations

from django.apps import AppConfig


class CommerceConfig(AppConfig):
    """Configures the commerce app — the product catalog (read side)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.commerce"
