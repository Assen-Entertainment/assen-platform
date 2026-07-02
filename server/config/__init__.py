"""Assen Platform Django project package.

Ensures the Celery app is imported when Django starts so shared_task discovery
works (see config.celery).
"""

from __future__ import annotations

from config.celery import app as celery_app

__all__ = ("celery_app",)
