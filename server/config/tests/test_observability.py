"""Tests for the observability layer (R4-W2, ASS-242): Sentry gate, PII scrubber,
structured JSON logging, and request-id log correlation.

No database access is required — these exercise pure functions and the logging
primitives directly.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, cast

import pytest

from config.observability import (
    JsonLogFormatter,
    RequestIDLogFilter,
    _scrub_event,
    bind_request_id,
    get_current_request_id,
    git_sha,
    init_sentry,
    unbind_request_id,
)


def _record(
    name: str = "apps.demo", msg: str = "hello", args: tuple[object, ...] | None = None
) -> logging.LogRecord:
    """Build a bare LogRecord for formatter/filter tests."""
    return logging.LogRecord(name, logging.INFO, __file__, 10, msg, args, None)


# --------------------------------------------------------------------------- #
# Sentry gate — no-op unless SENTRY_DSN is set
# --------------------------------------------------------------------------- #


def test_init_sentry_is_noop_without_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no SENTRY_DSN, init_sentry never touches the SDK (dev/test safe)."""
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    import sentry_sdk

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))

    init_sentry()

    assert calls == []


def test_init_sentry_wires_django_integration_when_dsn_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A DSN initialises Sentry with PII off, the scrubber, and env/trace config."""
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.ingest.sentry.io/42")
    monkeypatch.setenv("DJANGO_ENV", "staging")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.25")
    import sentry_sdk

    captured: dict[str, object] = {}
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: captured.update(kwargs))

    init_sentry()

    assert str(captured["dsn"]).endswith("/42")
    assert captured["environment"] == "staging"
    assert captured["traces_sample_rate"] == 0.25
    # PII must be off and the scrubber must run before anything is sent.
    assert captured["send_default_pii"] is False
    assert callable(captured["before_send"])
    assert captured["integrations"]  # DjangoIntegration attached


# --------------------------------------------------------------------------- #
# before_send scrubber — redact PII / secrets / forbidden narrative
# --------------------------------------------------------------------------- #


def test_scrub_event_redacts_pii_secrets_and_forbidden_keys() -> None:
    """Sensitive values are blanked anywhere in the event; benign ones survive."""
    event: dict[str, Any] = {
        "request": {
            "headers": {
                "Authorization": "Bearer super-secret",
                "Content-Type": "application/json",
            },
            "data": {
                "phone": "010-1234-5678",
                "message": "raw report narrative",  # FORBIDDEN_SAFETY_PROPERTY_KEYS
                "note": "keep me",
            },
        },
        "extra": {"access_token": "abc123", "count": 3},
        "breadcrumbs": [{"data": {"narrative": "raw text", "ok": 1}}],
        "user": {"id": "u1"},
    }

    # Scrubbing is in place; assert against the original dict (typed, indexable).
    result = _scrub_event(cast(Any, event), cast(Any, {}))
    assert result is event  # returned, never dropped

    # High-signal header + PII + secret token → redacted.
    assert event["request"]["headers"]["Authorization"] == "[Filtered]"
    assert event["request"]["data"]["phone"] == "[Filtered]"
    assert event["extra"]["access_token"] == "[Filtered]"
    # Reused forbidden-safety keys → redacted (even nested inside a list).
    assert event["request"]["data"]["message"] == "[Filtered]"
    assert event["breadcrumbs"][0]["data"]["narrative"] == "[Filtered]"
    # Benign fields untouched.
    assert event["request"]["headers"]["Content-Type"] == "application/json"
    assert event["request"]["data"]["note"] == "keep me"
    assert event["extra"]["count"] == 3
    assert event["user"]["id"] == "u1"


# --------------------------------------------------------------------------- #
# Structured JSON logging
# --------------------------------------------------------------------------- #


def test_json_log_formatter_emits_one_json_object() -> None:
    """A record renders to a single JSON line with the standard fields."""
    record = _record(msg="hello %s", args=("world",))
    record.request_id = "req-123"

    obj = json.loads(JsonLogFormatter().format(record))

    assert obj["level"] == "INFO"
    assert obj["logger"] == "apps.demo"
    assert obj["message"] == "hello world"
    assert obj["request_id"] == "req-123"
    assert "timestamp" in obj


def test_json_log_formatter_includes_exception() -> None:
    """exc_info is serialised into an `exception` field."""
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            "apps.demo", logging.ERROR, __file__, 10, "failed", None, sys.exc_info()
        )

    obj = json.loads(JsonLogFormatter().format(record))

    assert "ValueError" in obj["exception"]
    assert "boom" in obj["exception"]


def test_json_log_formatter_defaults_request_id_when_unbound() -> None:
    """A record with no request_id attribute still serialises (defaults to '-')."""
    obj = json.loads(JsonLogFormatter().format(_record()))
    assert obj["request_id"] == "-"


# --------------------------------------------------------------------------- #
# Request-id correlation
# --------------------------------------------------------------------------- #


def test_request_id_filter_stamps_bound_id() -> None:
    """The filter copies the bound context id onto the record."""
    filt = RequestIDLogFilter()
    record = _record()
    token = bind_request_id("abc123")
    try:
        assert filt.filter(record) is True
        assert getattr(record, "request_id") == "abc123"  # noqa: B009 - dynamic attr
    finally:
        unbind_request_id(token)


def test_request_id_defaults_outside_request() -> None:
    """Outside a request the id is the '-' sentinel."""
    filt = RequestIDLogFilter()
    record = _record()

    assert filt.filter(record) is True
    assert getattr(record, "request_id") == "-"  # noqa: B009 - dynamic attr
    assert get_current_request_id() == "-"


# --------------------------------------------------------------------------- #
# git_sha metadata
# --------------------------------------------------------------------------- #


def test_git_sha_prefers_git_sha_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """GIT_SHA wins over COMMIT_SHA and the git subprocess."""
    monkeypatch.setenv("GIT_SHA", "deadbeef")
    monkeypatch.setenv("COMMIT_SHA", "cafef00d")
    assert git_sha() == "deadbeef"


def test_git_sha_falls_back_to_commit_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    """COMMIT_SHA is used when GIT_SHA is unset (existing Docker convention)."""
    monkeypatch.delenv("GIT_SHA", raising=False)
    monkeypatch.setenv("COMMIT_SHA", "cafef00d")
    assert git_sha() == "cafef00d"
