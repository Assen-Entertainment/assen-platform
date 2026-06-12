"""App configuration for the admin_rbac domain."""

from __future__ import annotations

from django.apps import AppConfig


class AdminRbacConfig(AppConfig):
    """Configures the admin_rbac app (P4 foundation: RBAC guards + redaction)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admin_rbac"
