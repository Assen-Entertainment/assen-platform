"""ASS-287 A-1 — /api/capabilities reflects the runtime gate flags.

The web reads this single source instead of duplicating the server flags (which
would drift). Only availability booleans are exposed — no secrets.
"""

from __future__ import annotations

import pytest
from django.test import Client, override_settings

pytestmark = pytest.mark.django_db


@override_settings(ENABLE_SHIPPING_CHECKOUT=False, ENABLE_MOCK_PAYMENT=True)
def test_capabilities_reports_gate_flags(client: Client) -> None:
    body = client.get("/api/capabilities").json()
    assert body["shipping_checkout_available"] is False
    assert body["payment_available"] is True


@override_settings(ENABLE_SHIPPING_CHECKOUT=True)
def test_capabilities_reflects_open_shipping(client: Client) -> None:
    body = client.get("/api/capabilities").json()
    assert body["shipping_checkout_available"] is True
