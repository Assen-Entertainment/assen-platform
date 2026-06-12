"""App configuration for the audit domain."""

from __future__ import annotations

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Configures the audit app (P4 foundation: privileged-action AuditEntry)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
