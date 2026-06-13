"""App configuration for the identity domain."""

from __future__ import annotations

from django.apps import AppConfig


class IdentityConfig(AppConfig):
    """Configures the identity app (P4 foundation: accounts + opaque tokens)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.identity"
