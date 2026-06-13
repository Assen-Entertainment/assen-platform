"""App configuration for the notification domain."""

from __future__ import annotations

from django.apps import AppConfig


class NotificationConfig(AppConfig):
    """Configures the notification app (P4 foundation: push adapter interface)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notification"
