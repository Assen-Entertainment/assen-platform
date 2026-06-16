"""App configuration for the visit_guide domain."""

from __future__ import annotations

from django.apps import AppConfig


class VisitGuideConfig(AppConfig):
    """Configures the visit_guide app (F02 visit info/rules CMS, ASS-101 v0)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.visit_guide"
