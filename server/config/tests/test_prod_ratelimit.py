"""ASS-295 — production requires a shared, proxy-aware rate limiter at boot.

The per-process in-memory limiter cannot bound a multi-worker fleet, and a wrong
proxy-hop count buckets every user onto the load-balancer IP. prod fails closed at
import when the shared Redis backend or an explicit proxy-hop count is missing.
"""

from __future__ import annotations

import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured


def _base_prod_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The other prod-required env so the import reaches the rate-limit checks."""
    monkeypatch.setenv("DJANGO_SECRET_KEY", "prod-smoke-secret-not-real")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "prod.example")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@localhost:5432/prod")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    monkeypatch.setenv(
        "PHONE_IDENTIFIER_HMAC_KEY", "prod-smoke-phone-hmac-key-not-real-0123456789"
    )


def _import_prod() -> object:
    sys.modules.pop("config.settings.prod", None)
    return importlib.import_module("config.settings.prod")


def test_prod_boots_with_shared_ratelimit(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_prod_env(monkeypatch)
    monkeypatch.setenv("RATELIMIT_BACKEND", "redis")
    monkeypatch.setenv("RATELIMIT_REDIS_URL", "redis://localhost:6379/2")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    prod = _import_prod()
    assert prod.DEBUG is False  # type: ignore[attr-defined]


def test_prod_refuses_in_memory_ratelimit(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_prod_env(monkeypatch)
    monkeypatch.delenv("RATELIMIT_BACKEND", raising=False)  # defaults to "memory"
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    with pytest.raises(ImproperlyConfigured, match="RATELIMIT_BACKEND"):
        _import_prod()


def test_prod_refuses_zero_proxy_hops(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_prod_env(monkeypatch)
    monkeypatch.setenv("RATELIMIT_BACKEND", "redis")
    monkeypatch.setenv("RATELIMIT_REDIS_URL", "redis://localhost:6379/2")
    monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)  # defaults to 0
    with pytest.raises(ImproperlyConfigured, match="TRUSTED_PROXY_HOPS"):
        _import_prod()
