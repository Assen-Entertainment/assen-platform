"""Smoke test for the event_campaign app. Asserts the app is installed; no DB access."""

from __future__ import annotations

from django.apps import apps


def test_event_campaign_app_is_installed() -> None:
    """The event_campaign app is registered in the Django app registry."""
    assert apps.is_installed("apps.event_campaign")
