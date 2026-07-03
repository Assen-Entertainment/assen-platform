"""App configuration for the payments domain (saved payment methods; R3)."""

from __future__ import annotations

from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    """Configures the payments app — saved payment methods (brand + last4 + token)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
