from django.apps import AppConfig


class CommerceBridgeConfig(AppConfig):
    """Hosted-commerce bridge — provider-agnostic integration seam (fail-closed)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.commerce_bridge"
