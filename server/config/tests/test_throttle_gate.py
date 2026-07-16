"""The fan-throttle gate is evaluated per request, not frozen at import.

Regression guard for the ``config.throttle`` footgun: the helpers used to read
``FAN_WRITE_THROTTLE_ENABLED`` at decoration time and freeze an empty list into the
operation, so ``override_settings`` could not turn throttling back on at test time.
Now each helper wraps its rate throttle in ``_FlagGatedThrottle`` whose
``allow_request`` reads the flag on every call, so both directions are testable:

- flag off (the default test setting) → every request is allowed (no 429), and
- flag on (via ``override_settings``) → the rate is actually enforced (429).

The email-signup endpoint (``anon_throttle("10/min")``) is the probe; it needs no
auth, returns 200 on a valid (idempotent re-signup) body, and has a low,
deterministic limit.
"""

from __future__ import annotations

import json

import pytest
from django.core.cache import cache
from django.test import Client, override_settings

pytestmark = pytest.mark.django_db

_PROBE_URL = "/api/fan/signup/email"
_BODY = json.dumps(
    {
        "email": "throttle@example.com",
        "password": "correct horse 8",
        "nickname": "쓰로틀",
        "consent_terms": True,
        "consent_privacy": True,
        "age_over_14": True,
    }
)


def _send(client: Client) -> int:
    return int(
        client.post(_PROBE_URL, data=_BODY, content_type="application/json").status_code
    )


def test_gate_off_allows_every_request(client: Client) -> None:
    """With the flag off (default test setting) the bucket never fills."""
    cache.clear()
    try:
        for _ in range(13):  # well past the 10/min rate — none should be throttled
            assert _send(client) == 200
    finally:
        cache.clear()


@override_settings(FAN_WRITE_THROTTLE_ENABLED=True)
def test_gate_on_enforces_rate_at_request_time(client: Client) -> None:
    """override_settings now re-enables throttling — proof the gate is request-time."""
    cache.clear()
    try:
        for _ in range(10):  # the 10/min allowance
            assert _send(client) == 200
        assert _send(client) == 429  # the eleventh from the same IP is throttled
    finally:
        cache.clear()
