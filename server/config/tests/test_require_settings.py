"""ASS-285 — the ASGI/WSGI/Celery entrypoints require an explicit settings module.

No silent ``config.settings.dev`` fallback: a missing ``DJANGO_SETTINGS_MODULE``
must fail loudly rather than boot dev (DEBUG + every mock gate on) in production.
"""

from __future__ import annotations

import pytest

from config.require_settings import require_settings_module


def test_raises_when_settings_module_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    with pytest.raises(RuntimeError, match="DJANGO_SETTINGS_MODULE"):
        require_settings_module()


def test_ok_when_settings_module_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "config.settings.test")
    require_settings_module()  # does not raise
