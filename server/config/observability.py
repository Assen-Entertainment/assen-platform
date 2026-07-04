"""Observability primitives: error tracking, structured logging, health metadata.

Three fail-safe, gate-driven concerns live here (R4-W2, ASS-242/B8):

- **Sentry** (:func:`init_sentry`) — a *no-op unless* ``SENTRY_DSN`` is set, so dev
  and test are never touched and production only reports when explicitly wired.
  A ``before_send`` scrubber (:func:`_scrub_event`) redacts PII / secrets / raw
  report narrative before anything leaves the process, reusing the same forbidden
  key list the event pipeline enforces (``FORBIDDEN_SAFETY_PROPERTY_KEYS``).
- **Request-id log correlation** — a :class:`contextvars.ContextVar` bound by
  ``RequestIDMiddleware`` and read back by :class:`RequestIDLogFilter`, so every
  log line can be traced to the request that produced it.
- **Structured logging** — :class:`JsonLogFormatter` emits one JSON object per
  record (prod); the human-readable console format (dev) is a plain format string
  in the settings ``LOGGING`` config.

This module imports **only the standard library at import time** — Django, the
Sentry SDK, and the app-layer forbidden-key list are all imported lazily inside
the functions that need them. That keeps it safe to import from a settings module
(``prod.py``) before the app registry is ready.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from collections.abc import Callable
from contextvars import ContextVar, Token
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Only needed to type the before_send hook; sentry_sdk is otherwise imported
    # lazily so this module stays stdlib-only at runtime import time.
    from sentry_sdk.types import Event, Hint

# --------------------------------------------------------------------------- #
# Request-id correlation
# --------------------------------------------------------------------------- #

# Bound per request by RequestIDMiddleware; read by RequestIDLogFilter. "-" is the
# out-of-request sentinel (management commands, Celery workers, boot-time logs).
_request_id_ctx: ContextVar[str] = ContextVar("assen_request_id", default="-")


def bind_request_id(request_id: str) -> Token[str]:
    """Bind ``request_id`` for the current context; return a reset token."""
    return _request_id_ctx.set(request_id)


def unbind_request_id(token: Token[str]) -> None:
    """Restore the previous request-id binding (call in a ``finally``)."""
    _request_id_ctx.reset(token)


def get_current_request_id() -> str:
    """Return the request id bound to the current context, or ``"-"``."""
    return _request_id_ctx.get()


class RequestIDLogFilter(logging.Filter):
    """Inject the current request id onto every record as ``request_id``.

    Referenced by dotted path from the settings ``LOGGING`` config so both the
    console and JSON formatters can render ``%(request_id)s`` / a ``request_id``
    field without each call site passing it explicitly.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Always keep the record; annotate it with the correlation id first."""
        record.request_id = get_current_request_id()
        return True


class JsonLogFormatter(logging.Formatter):
    """Render a log record as a single JSON object (one line, prod).

    Emits a fixed, safe allow-list of fields — never the record's arbitrary
    ``extra``/``args`` dict — so a stray sensitive value passed as logging context
    cannot be serialised into the log stream by accident.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Serialise the record to a compact JSON line."""
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Build / version metadata
# --------------------------------------------------------------------------- #


def git_sha() -> str:
    """Return the running commit hash for health/version surfaces.

    ``GIT_SHA`` (R4 convention) is tried first, then ``COMMIT_SHA`` (the existing
    Docker build arg), then a local ``git`` call, then ``"unknown"``. In a
    container both env vars are absent-or-set at build time, so the subprocess is
    only ever hit in a working tree.
    """
    for var in ("GIT_SHA", "COMMIT_SHA"):
        value = os.environ.get(var)
        if value:
            return value
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


# --------------------------------------------------------------------------- #
# Sentry (error tracking) — gated on SENTRY_DSN, PII-scrubbed
# --------------------------------------------------------------------------- #

# Placeholder written over any value whose key looks sensitive.
_REDACTED = "[Filtered]"

# Depth guard for the recursive scrubber — Sentry events are shallow JSON, but we
# never want a cyclic/pathological structure to spin.
_MAX_SCRUB_DEPTH = 25

# Keys (lowercased) whose values are always secrets/PII, independent of the safety
# event forbidden list. Union'd with FORBIDDEN_SAFETY_PROPERTY_KEYS at runtime.
_PII_SCRUB_KEYS: frozenset[str] = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "csrftoken",
        "x-csrftoken",
        "sessionid",
        "session",
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "otp",
        "otp_code",
        "phone",
        "phone_number",
        "tel",
        "mobile",
        "email",
        "ssn",
        "rrn",
        "resident_registration_number",
        "card_number",
        "pan",
        "cvc",
        "cvv",
        "contact",
    }
)

# Substrings that mark a key sensitive even when embedded (e.g. ``user_phone``,
# ``access_token``, ``x-auth-token``). Kept deliberately high-signal so the
# scrubber over-redacts rather than leaks (task priority: zero PII to Sentry).
_HIGH_SIGNAL_TOKENS: tuple[str, ...] = (
    "password",
    "passwd",
    "token",
    "secret",
    "authorization",
    "cookie",
    "phone",
    "card_number",
    "cvc",
    "cvv",
)


@lru_cache(maxsize=1)
def _forbidden_keys() -> frozenset[str]:
    """Return the lowercased set of keys the scrubber redacts on exact match.

    Reuses the event pipeline's ``FORBIDDEN_SAFETY_PROPERTY_KEYS`` (raw report
    narrative, contact, card_number, …) so the two enforcement points cannot drift.
    Imported lazily — the app registry is not ready when a settings module first
    imports this file.
    """
    try:
        from apps.event_log.events import FORBIDDEN_SAFETY_PROPERTY_KEYS
    except Exception:  # pragma: no cover - defensive; app import must never gate scrubbing
        return _PII_SCRUB_KEYS
    return frozenset(key.lower() for key in FORBIDDEN_SAFETY_PROPERTY_KEYS) | _PII_SCRUB_KEYS


def _is_sensitive_key(key: str, forbidden: frozenset[str]) -> bool:
    """Whether ``key`` names a value that must be redacted before send."""
    lowered = key.lower()
    if lowered in forbidden:
        return True
    return any(token in lowered for token in _HIGH_SIGNAL_TOKENS)


def _redact_in_place(obj: Any, is_sensitive: Callable[[str], bool], depth: int) -> None:
    """Recursively blank out sensitive values in a nested dict/list, in place."""
    if depth > _MAX_SCRUB_DEPTH:
        return
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if isinstance(key, str) and is_sensitive(key):
                obj[key] = _REDACTED
            else:
                _redact_in_place(value, is_sensitive, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _redact_in_place(item, is_sensitive, depth + 1)


def _scrub_event(event: Event, hint: Hint) -> Event:
    """Sentry ``before_send`` hook: redact PII / secrets / raw narrative in place.

    Belt-and-suspenders on top of ``send_default_pii=False``: walks the whole
    event (request headers/body, extra, breadcrumbs, contexts) and blanks any key
    that matches the forbidden/PII set. Always returns the event — scrubbing must
    never drop error signal, only sanitise it.
    """
    del hint  # unused; present to match the Sentry before_send signature
    forbidden = _forbidden_keys()

    def _pred(key: str) -> bool:
        return _is_sensitive_key(key, forbidden)

    _redact_in_place(event, _pred, 0)
    return event


def init_sentry() -> None:
    """Initialise Sentry error tracking — a **no-op unless ``SENTRY_DSN`` is set**.

    Fail-safe by construction: with no DSN (dev, test, and any unconfigured
    deploy) nothing is imported or initialised. When a DSN is present it wires the
    Django integration with ``send_default_pii=False`` and the PII scrubber, reads
    the environment tag from ``DJANGO_ENV`` and the trace sample rate from
    ``SENTRY_TRACES_SAMPLE_RATE`` (default 0.0 — tracing off until deliberately
    dialed up).
    """
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    try:
        traces_sample_rate = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
    except ValueError:
        traces_sample_rate = 0.0

    sentry_sdk.init(
        dsn=dsn,
        integrations=[DjangoIntegration()],
        environment=os.environ.get("DJANGO_ENV", "production"),
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        before_send=_scrub_event,
    )
