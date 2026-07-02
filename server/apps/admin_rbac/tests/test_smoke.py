"""Smoke test for the admin_rbac app. Asserts the app is installed; no DB access."""

from __future__ import annotations

from django.apps import apps


def test_admin_rbac_app_is_installed() -> None:
    """The admin_rbac app is registered in the Django app registry."""
    assert apps.is_installed("apps.admin_rbac")
