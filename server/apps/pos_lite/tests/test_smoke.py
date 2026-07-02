"""Smoke test for the pos_lite app. Asserts the app is installed; no DB access."""

from __future__ import annotations

from django.apps import apps


def test_pos_lite_app_is_installed() -> None:
    """The pos_lite app is registered in the Django app registry."""
    assert apps.is_installed("apps.pos_lite")
