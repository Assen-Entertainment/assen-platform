"""App configuration for the event_log domain."""

from __future__ import annotations

from django.apps import AppConfig


class EventLogConfig(AppConfig):
    """Configures the event_log app (P4 foundation: append-only EventRecord)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.event_log"
