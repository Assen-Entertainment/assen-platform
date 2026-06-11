"""Smoke test for the visit app. Asserts the app is installed; no DB access."""

from __future__ import annotations

from django.apps import apps


def test_visit_app_is_installed() -> None:
    """The visit app is registered in the Django app registry."""
    assert apps.is_installed("apps.visit")
