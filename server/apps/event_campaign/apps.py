"""App configuration for the event_campaign domain."""

from __future__ import annotations

from django.apps import AppConfig


class EventCampaignConfig(AppConfig):
    """Configures the event_campaign app (F10 event announcements, ASS-107 v0)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.event_campaign"
