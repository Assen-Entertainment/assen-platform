"""App configuration for the feature_flag domain."""

from __future__ import annotations

from django.apps import AppConfig


class FeatureFlagConfig(AppConfig):
    """Configures the feature_flag app (P4 foundation: FeatureFlag + seeds)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.feature_flag"
