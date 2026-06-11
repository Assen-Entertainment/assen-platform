"""App configuration for the reservation domain."""

from __future__ import annotations

from django.apps import AppConfig


class ReservationConfig(AppConfig):
    """Configures the reservation app. Models arrive in P4/P5 (empty in P0)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reservation"
