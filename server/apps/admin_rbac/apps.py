"""App configuration for the admin_rbac domain."""

from __future__ import annotations

from django.apps import AppConfig


class AdminRbacConfig(AppConfig):
    """Configures the admin_rbac app. Models arrive in P4/P5 (empty in P0)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admin_rbac"
