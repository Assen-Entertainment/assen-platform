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

The gate is evaluated **per request**, not at decoration time. Each helper wraps
its rate throttle in a :class:`_FlagGatedThrottle`, whose ``allow_request`` reads
``FAN_WRITE_THROTTLE_ENABLED`` on every call: when the flag is off it short-circuits
to *allow* without touching the cache (so the suite stays deterministic), and when
on it delegates to the real rate throttle. This is what lets a test flip the flag
with ``override_settings(FAN_WRITE_THROTTLE_ENABLED=True)`` and actually exercise the
429 path — the older decoration-time gate froze an empty list into the operation at
import, so ``override_settings`` had no effect (see
``config/tests/test_throttle_gate.py``).
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest
from ninja.throttling import AnonRateThrottle, AuthRateThrottle, BaseThrottle

from config.clientip import client_ip


def _throttle_enabled() -> bool:
    """Read the throttle gate at *request* time (see module note)."""
    return bool(getattr(settings, "FAN_WRITE_THROTTLE_ENABLED", True))


class _FlagGatedThrottle(BaseThrottle):
    """Defer the ``FAN_WRITE_THROTTLE_ENABLED`` check to ``allow_request``.

    Wrapping the real rate throttle (rather than returning ``[]`` at decoration
    time) means the flag is consulted per request: off → allow immediately (no
    cache hit, so tests stay deterministic); on → delegate to ``inner``. ``wait``
    forwards to ``inner`` so a 429 still reports the correct ``Retry-After``.
    """

    def __init__(self, inner: BaseThrottle) -> None:
        """Wrap ``inner`` (the real per-user/per-IP rate throttle)."""
        self.inner = inner

    def allow_request(self, request: HttpRequest) -> bool:
        """Allow unconditionally when the gate is off, else defer to ``inner``."""
        if not _throttle_enabled():
            return True
        return self.inner.allow_request(request)

    def wait(self) -> float | None:
        """Forward the recommended wait from the inner throttle."""
        return self.inner.wait()


class _ClientIPIdentMixin:
    """Key IP-based throttling on :func:`~config.clientip.client_ip`.

    Ninja's ``get_ident`` reads XFF via its own ``NUM_PROXIES`` setting; overriding
    it makes the ninja throttles and the middleware limiter share one trusted-proxy
    policy (``TRUSTED_PROXY_HOPS``). With the default 0 hops this returns
    ``REMOTE_ADDR`` — identical to the previous behaviour — but behind an ALB it
    keys on the real client instead of the shared balancer address.
    """

    def get_ident(self, request: HttpRequest) -> str:
        """Identify the client via the shared trusted-proxy-aware extractor."""
        return client_ip(request)


class XFFAnonRateThrottle(_ClientIPIdentMixin, AnonRateThrottle):
    """Per-client anonymous throttle keyed on the trusted-proxy-aware client IP."""


class XFFAuthRateThrottle(_ClientIPIdentMixin, AuthRateThrottle):
    """Per-user throttle; anonymous fallback keys on the trusted-proxy-aware IP."""


def user_write_throttle(rate: str) -> list[BaseThrottle]:
    """Return a per-user rate throttle for ``rate`` (e.g. ``"60/min"``).

    The returned throttle is flag-gated per request (:class:`_FlagGatedThrottle`):
    when ``FAN_WRITE_THROTTLE_ENABLED`` is false (tests) it allows every request
    without touching the cache; when true it enforces ``rate`` per account.
    """
    return [_FlagGatedThrottle(XFFAuthRateThrottle(rate))]


def anon_throttle(rate: str) -> list[BaseThrottle]:
    """Return a per-IP rate throttle for ``rate`` (e.g. ``"5/min"``).

    For unauthenticated entry points (signup/OTP/login) an attacker has no
    ``request.auth``, so the throttle keys on the client IP instead. Gated per
    request by the same ``FAN_WRITE_THROTTLE_ENABLED`` flag as
    :func:`user_write_throttle` (see :class:`_FlagGatedThrottle`).
    """
    return [_FlagGatedThrottle(XFFAnonRateThrottle(rate))]
