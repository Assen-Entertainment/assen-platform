"""Smoke test for the feature_flag app. Asserts the app is installed; no DB access."""

from __future__ import annotations

from django.apps import apps


def test_feature_flag_app_is_installed() -> None:
    """The feature_flag app is registered in the Django app registry."""
    assert apps.is_installed("apps.feature_flag")
