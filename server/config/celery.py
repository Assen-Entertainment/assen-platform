"""Celery application for Assen Platform (ADR-0001).

Standard Django integration: configuration is namespaced under CELERY_* in
Django settings, and tasks are auto-discovered from every installed app. The
beat schedule is a placeholder (CELERY_BEAT_SCHEDULE in settings) until periodic
jobs such as billing retries are introduced in later phases.
"""

from __future__ import annotations

from celery import Celery

from config.require_settings import require_settings_module

require_settings_module()

app = Celery("assen")

# Pull all CELERY_-prefixed settings from Django config.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover tasks.py modules in every installed app.
app.autodiscover_tasks()
