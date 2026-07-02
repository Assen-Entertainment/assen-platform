"""Smoke test for the cheki app. Asserts the app is installed; no DB access."""

from __future__ import annotations

from django.apps import apps


def test_cheki_app_is_installed() -> None:
    """The cheki app is registered in the Django app registry."""
    assert apps.is_installed("apps.cheki")
