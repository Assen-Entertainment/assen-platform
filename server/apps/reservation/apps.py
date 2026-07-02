"""App configuration for the reservation domain."""

from __future__ import annotations

from django.apps import AppConfig


class ReservationConfig(AppConfig):
    """Configures the reservation app (F03 reservation/waitlist, ASS-109 v0)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reservation"
