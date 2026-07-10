"""Tests for Channels layer selection (config.settings.base._build_channel_layers,
ASS-268 follow-up: wiring the shared cross-worker channels-redis layer).

``_build_channel_layers()`` fails safe to the in-memory layer unless
``CHANNEL_LAYERS_BACKEND == "redis"`` AND ``channels_redis`` is importable AND
``CHANNEL_LAYERS_REDIS_URL`` is set (see the docstring/comment in base.py). It reads
``CHANNEL_LAYERS_BACKEND`` as a plain module global — captured once when
config.settings.base is imported — and ``CHANNEL_LAYERS_REDIS_URL`` via ``env()``
(os.environ) at call time. So these tests monkeypatch the module attribute / env var
directly rather than ``django.test.override_settings``: override_settings only
patches ``django.conf.settings``, which this function never consults (it is not
django-settings-aware, by design — it runs *while* settings are being built).
"""

from __future__ import annotations

import pytest

from config.settings import base as base_settings
from config.settings.base import _build_channel_layers

_IN_MEMORY = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def test_build_channel_layers_defaults_to_in_memory() -> None:
    # The test settings module never sets CHANNEL_LAYERS_BACKEND, so it keeps
    # base.py's own "memory" default.
    assert base_settings.CHANNEL_LAYERS_BACKEND == "memory"
    assert _build_channel_layers() == _IN_MEMORY


def test_build_channel_layers_redis_backend_without_url_fails_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(base_settings, "CHANNEL_LAYERS_BACKEND", "redis")
    monkeypatch.delenv("CHANNEL_LAYERS_REDIS_URL", raising=False)
    assert _build_channel_layers() == _IN_MEMORY


def test_build_channel_layers_selects_redis_channel_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # channels-redis lives in the OPTIONAL `realtime-redis` extra and is not installed
    # in dev/test by default (CI runs `uv sync --frozen` without the extra). Skip when
    # it is absent so this asserts layer *selection* only where the extra is present
    # (prod-parity venv / the Dockerfile's `--extra realtime-redis` image), and stays
    # green in CI — matching _build_channel_layers()'s own ImportError fail-safe. No
    # live Redis connection is required (RedisChannelLayer.__init__ does not connect).
    pytest.importorskip("channels_redis")
    monkeypatch.setattr(base_settings, "CHANNEL_LAYERS_BACKEND", "redis")
    monkeypatch.setenv("CHANNEL_LAYERS_REDIS_URL", "redis://localhost:6379/3")

    layers = _build_channel_layers()

    assert layers["default"]["BACKEND"] == "channels_redis.core.RedisChannelLayer"
    assert layers["default"]["CONFIG"]["hosts"] == ["redis://localhost:6379/3"]


def test_build_channel_layers_non_redis_backend_ignores_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(base_settings, "CHANNEL_LAYERS_BACKEND", "something-else")
    monkeypatch.setenv("CHANNEL_LAYERS_REDIS_URL", "redis://localhost:6379/3")
    assert _build_channel_layers() == _IN_MEMORY
