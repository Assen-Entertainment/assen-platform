"""Tests for trusted-proxy-aware client IP extraction (R5-W1A).

Covers the default (0 hops → REMOTE_ADDR, dev unchanged), the behind-a-proxy
selection from X-Forwarded-For, spoofing resistance (a client-forged prefix cannot
displace the trusted tail), clamping for short chains, and the settings-driven
default hop count.
"""

from __future__ import annotations

from django.http import HttpRequest
from django.test import RequestFactory, override_settings

from config.clientip import client_ip

_RF = RequestFactory()


def _req(remote: str = "10.0.0.1", xff: str | None = None) -> HttpRequest:
    """Build a request with ``REMOTE_ADDR`` and optional ``X-Forwarded-For``."""
    request = _RF.get("/")
    request.META["REMOTE_ADDR"] = remote
    if xff is not None:
        request.META["HTTP_X_FORWARDED_FOR"] = xff
    return request


def test_zero_hops_returns_remote_addr() -> None:
    # With no trusted proxy, XFF is ignored entirely (dev/no-proxy behaviour).
    assert client_ip(_req(remote="10.0.0.1", xff="1.2.3.4"), trusted_proxies=0) == "10.0.0.1"


def test_one_hop_takes_the_appended_client() -> None:
    # A single ALB appends the real client last; 1 hop selects that rightmost entry.
    assert client_ip(_req(xff="203.0.113.7"), trusted_proxies=1) == "203.0.113.7"


def test_one_hop_ignores_client_forged_prefix() -> None:
    # A forged left entry cannot displace the address the trusted proxy appended.
    assert client_ip(_req(xff="9.9.9.9, 203.0.113.7"), trusted_proxies=1) == "203.0.113.7"


def test_two_hops_selects_client_past_two_proxies() -> None:
    got = client_ip(_req(xff="9.9.9.9, 203.0.113.7, 10.0.0.2"), trusted_proxies=2)
    assert got == "203.0.113.7"


def test_hops_clamp_to_leftmost_for_short_chain() -> None:
    # More declared hops than entries clamps to the head — never before it.
    assert client_ip(_req(xff="203.0.113.7, 10.0.0.2"), trusted_proxies=5) == "203.0.113.7"


def test_missing_xff_falls_back_to_remote_addr() -> None:
    assert client_ip(_req(remote="10.0.0.9"), trusted_proxies=1) == "10.0.0.9"


def test_empty_xff_falls_back_to_remote_addr() -> None:
    assert client_ip(_req(remote="10.0.0.9", xff="  ,  "), trusted_proxies=1) == "10.0.0.9"


def test_negative_hops_treated_as_zero() -> None:
    assert client_ip(_req(remote="10.0.0.1", xff="1.2.3.4"), trusted_proxies=-3) == "10.0.0.1"


@override_settings(TRUSTED_PROXY_HOPS=1)
def test_default_uses_settings_hops() -> None:
    assert client_ip(_req(xff="9.9.9.9, 203.0.113.7")) == "203.0.113.7"


@override_settings(TRUSTED_PROXY_HOPS=0)
def test_default_zero_hops_from_settings() -> None:
    assert client_ip(_req(remote="10.0.0.1", xff="1.2.3.4")) == "10.0.0.1"
