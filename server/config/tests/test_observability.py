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
                # ``message`` is banned in the event-log domain but a legitimate
                # Sentry signal — it must NOT be key-blanked (R-A regression guard).
                "message": "raw report narrative",
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
    # A Sentry ``message`` is a legitimate signal (not a forbidden narrative here):
    # it survives the key scrub. Value-scrub still runs, but this text carries no PII
    # so it is preserved verbatim — blanking it would destroy observability signal.
    assert event["request"]["data"]["message"] == "raw report narrative"
    # A genuinely forbidden key (narrative) is still blanked, even nested in a list.
    assert event["breadcrumbs"][0]["data"]["narrative"] == "[Filtered]"
    # Benign fields untouched.
    assert event["request"]["headers"]["Content-Type"] == "application/json"
    assert event["request"]["data"]["note"] == "keep me"
    assert event["extra"]["count"] == 3
    assert event["user"]["id"] == "u1"


def test_scrub_event_redacts_free_text_pii_in_values() -> None:
    """Value-based scrub catches PII/secrets embedded in string values (benign keys).

    Key-based redaction cannot see a phone number or token inside an exception
    message or a URL query, so the value pass must sanitise them in place while
    keeping the surrounding text.
    """
    event: dict[str, Any] = {
        "exception": {
            "values": [
                {"type": "ValueError", "value": "otp fail 010-1234-5678 token=abc123DEF456"}
            ]
        },
        "request": {
            "url": "https://api.assen.example/fan/login?token=secretVALUE0&foo=bar",
            "query_string": "phone=+82-10-9876-5432&page=2",
        },
        # A benign key (not in the forbidden/PII key set) so the *value* pass — not
        # key-based redaction — is what must catch the embedded Bearer credential.
        "extra": {"trace": "auth header was Bearer eyJhbGciOi.JIUzI1NiIs"},
    }

    _scrub_event(cast(Any, event), cast(Any, {}))

    exc_value = event["exception"]["values"][0]["value"]
    assert "010-1234-5678" not in exc_value  # phone redacted
    assert "abc123DEF456" not in exc_value  # token value redacted
    assert exc_value.startswith("otp fail ")  # surrounding text preserved
    assert "[Filtered]" in exc_value

    url = event["request"]["url"]
    assert "secretVALUE0" not in url  # ?token= value redacted
    assert "foo=bar" in url  # benign query param preserved

    qs = event["request"]["query_string"]
    assert "+82-10-9876-5432" not in qs  # +82 phone form redacted
    assert "page=2" in qs

    trace = event["extra"]["trace"]
    assert "eyJhbGciOi.JIUzI1NiIs" not in trace  # Bearer credential redacted
    assert "Bearer [Filtered]" in trace  # scheme kept, credential redacted


def test_scrub_event_preserves_message_but_value_scrubs_its_pii() -> None:
    """A Sentry ``message`` is the error signal, not PII (R-A regression guard).

    ``message`` is banned as a free-narrative key in the event-log domain, but for a
    Sentry event it is the primary display text — key-blanking it wholesale destroys
    the observability signal. So a clean message survives verbatim, and a message
    carrying PII is only *value*-scrubbed (phone / ``token=`` spans redacted in
    place), never dropped.
    """
    event: dict[str, Any] = {
        # Top-level event message with no PII → preserved verbatim.
        "message": "checkout failed for order 42",
        # A logentry message carrying PII → value-scrubbed in place, text kept.
        "logentry": {"message": "user 010-1234-5678 hit token=abc123DEF456 error"},
    }

    _scrub_event(cast(Any, event), cast(Any, {}))

    # Clean message text survives — the key scrub must not touch it.
    assert event["message"] == "checkout failed for order 42"
    # A message carrying PII is value-scrubbed (spans redacted, surrounding text kept).
    entry = event["logentry"]["message"]
    assert "010-1234-5678" not in entry  # phone redacted
    assert "abc123DEF456" not in entry  # token value redacted
    assert entry.startswith("user ")  # surrounding text preserved
    assert entry.endswith(" error")
    assert "[Filtered]" in entry


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
    git_sha.cache_clear()  # memoised (lru_cache); clear so this env is re-read
    monkeypatch.setenv("GIT_SHA", "deadbeef")
    monkeypatch.setenv("COMMIT_SHA", "cafef00d")
    assert git_sha() == "deadbeef"


def test_git_sha_falls_back_to_commit_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    """COMMIT_SHA is used when GIT_SHA is unset (existing Docker convention)."""
    git_sha.cache_clear()  # memoised (lru_cache); clear so this env is re-read
    monkeypatch.delenv("GIT_SHA", raising=False)
    monkeypatch.setenv("COMMIT_SHA", "cafef00d")
    assert git_sha() == "cafef00d"


def test_git_sha_is_memoised(monkeypatch: pytest.MonkeyPatch) -> None:
    """After the first read the value is cached — a later env change is ignored."""
    git_sha.cache_clear()
    monkeypatch.setenv("GIT_SHA", "first000")
    assert git_sha() == "first000"
    monkeypatch.setenv("GIT_SHA", "second00")
    assert git_sha() == "first000"  # cached; not re-read until cache_clear()
    git_sha.cache_clear()  # leave the cache clean for other tests
