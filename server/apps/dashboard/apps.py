"""App configuration for the operator dashboard (ASS-97).

No models: the dashboard is a read-only projection over the event ledger and an
operator API. Aggregation lives in ``apps.event_log.services`` (which owns the
``EventRecord`` it reads); this app contributes the operator surface + usage log.
"""

from __future__ import annotations

from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Configures the operator dashboard app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
