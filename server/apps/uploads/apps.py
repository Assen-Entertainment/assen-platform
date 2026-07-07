"""App configuration for the uploads domain (image upload → mock storage; R11)."""

from __future__ import annotations

from django.apps import AppConfig


class UploadsConfig(AppConfig):
    """Configures the uploads app — validated image upload to the storage backend."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.uploads"
