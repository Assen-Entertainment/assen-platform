"""Rate throttles for the fan surface (SDLC 09 §4, E11/B4; A4).

Two flavours:

- :func:`user_write_throttle` — per *authenticated user*, for the fan write
  endpoints (follow, like, comment, post). Ninja's
  :class:`~ninja.throttling.AuthRateThrottle` keys on ``str(request.auth)`` — for
  our :class:`~apps.identity.models.Account` that is ``"<role>:<fan_id>"`` (its
  ``__str__``), i.e. one bucket per account.
- :func:`anon_throttle` — per *client IP*, for the pre-auth entry points (signup
  OTP, signup, login) which have no ``request.auth`` to key on. Backed by
  :class:`~ninja.throttling.AnonRateThrottle` (keys on the request IP).

Both are gated by ``FAN_WRITE_THROTTLE_ENABLED`` so the test suite (which fires
many requests for the same fixture user/IP) can disable it and stay
deterministic — otherwise the shared LocMem cache would leak throttle state
across tests.

TRAP — the gate is evaluated at *decoration time*, not per request. Each helper
runs ``getattr(settings, "FAN_WRITE_THROTTLE_ENABLED", ...)`` once, when the
``@router`` decorator that receives its return value is imported. The operation
captures that result (an empty list, or a throttle list) permanently. So a test
that flips the flag with ``override_settings(FAN_WRITE_THROTTLE_ENABLED=True)`` at
*run time* does NOT re-enable throttling — the operation already froze the empty
list at import. To exercise the 429 path a test must instead inject a throttle
onto the live (bound) operation object; see
``apps/identity/tests/test_auth_endpoints.py::test_signup_otp_is_ip_throttled``.
"""

from __future__ import annotations

from django.conf import settings
from ninja.throttling import AnonRateThrottle, AuthRateThrottle, BaseThrottle


def user_write_throttle(rate: str) -> list[BaseThrottle]:
    """Return a per-user rate throttle for ``rate`` (e.g. ``"60/min"``).

    Returns an empty list when ``FAN_WRITE_THROTTLE_ENABLED`` is false (tests),
    which Ninja treats as "no throttle" — no cache is touched.
    """
    if not getattr(settings, "FAN_WRITE_THROTTLE_ENABLED", True):
        return []
    return [AuthRateThrottle(rate)]


def anon_throttle(rate: str) -> list[BaseThrottle]:
    """Return a per-IP rate throttle for ``rate`` (e.g. ``"5/min"``).

    For unauthenticated entry points (signup/OTP/login) an attacker has no
    ``request.auth``, so the throttle keys on the client IP instead. Gated by the
    same ``FAN_WRITE_THROTTLE_ENABLED`` flag as :func:`user_write_throttle`;
    returns an empty list (no throttle) when disabled. See the module TRAP note on
    why the gate cannot be re-enabled with ``override_settings`` at test time.
    """
    if not getattr(settings, "FAN_WRITE_THROTTLE_ENABLED", True):
        return []
    return [AnonRateThrottle(rate)]
