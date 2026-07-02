"""CORS wiring tests (SDLC 11 §4): closed by default, env-driven allow-list.

The browser-facing web app calls the API cross-origin, so corsheaders must
answer for configured origins — and stay silent (fail-closed) for everything
else. Uses /healthz + a preflight so no DB is touched.
"""

from __future__ import annotations

from django.test import Client, override_settings

WEB_ORIGIN = "http://web.example"


def test_cors_is_closed_by_default(client: Client) -> None:
    """No Access-Control-Allow-Origin unless the origin is explicitly allowed."""
    res = client.get("/healthz", HTTP_ORIGIN=WEB_ORIGIN)
    assert "Access-Control-Allow-Origin" not in res.headers


@override_settings(CORS_ALLOWED_ORIGINS=[WEB_ORIGIN])
def test_cors_allows_configured_origin(client: Client) -> None:
    """A configured web origin gets the CORS allow header back."""
    res = client.get("/healthz", HTTP_ORIGIN=WEB_ORIGIN)
    assert res.headers.get("Access-Control-Allow-Origin") == WEB_ORIGIN


@override_settings(CORS_ALLOWED_ORIGINS=[WEB_ORIGIN])
def test_cors_preflight_short_circuits(client: Client) -> None:
    """OPTIONS preflight is answered by the middleware with allow headers."""
    res = client.options(
        "/api/creators",
        HTTP_ORIGIN=WEB_ORIGIN,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
    )
    assert res.headers.get("Access-Control-Allow-Origin") == WEB_ORIGIN
