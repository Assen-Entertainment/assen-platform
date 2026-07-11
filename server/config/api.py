"""Single Ninja API instance for Assen Platform (ADR-0001, CONSTRAINTS #15).

Domain apps register their routers on this instance from their own api.py
modules. The schema this produces is the source for the Dart client codegen
pipeline (swagger_parser) in P6.
"""

from __future__ import annotations

import os
import subprocess

from django.conf import settings
from django.http import HttpRequest
from ninja import NinjaAPI, Schema

from config.errors import register_error_handlers

api = NinjaAPI(title="Assen Platform API", version="0.1.0")

# Render coded errors as {detail, code} (ASS-257). Additive: the default ninja
# HttpError handler ({detail} only) stays for raise sites without a code yet.
register_error_handlers(api)


class HealthResponse(Schema):
    """Health payload returned by the `/api/health` endpoint."""

    status: str
    version: str
    commit: str


def _resolve_git_commit() -> str:
    """Resolve the current git commit hash, or "unknown" if unavailable.

    Reads the COMMIT_SHA env var first (set in CI/containers where the .git
    directory is absent); falls back to invoking git for local development.
    """
    env_sha = os.environ.get("COMMIT_SHA")
    if env_sha:
        return env_sha
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


# Resolve the commit once at import (the value is fixed for the life of the
# process): the previous per-request ``git rev-parse`` spawned a subprocess on
# every ``/health`` hit — pure overhead for a value that never changes while the
# server runs, and a subprocess fork on the liveness path a load balancer polls.
_GIT_COMMIT = _resolve_git_commit()


@api.get("/health", response=HealthResponse)
def health(request: HttpRequest) -> HealthResponse:
    """Report liveness, API version, and the running commit hash.

    Ninja injects the request positionally; it is unused here but must be named
    without a leading underscore so the schema generator does not treat it as a
    request-body field.
    """
    del request
    return HealthResponse(
        status="ok",
        version=api.version,
        commit=_GIT_COMMIT,
    )


class CapabilitiesResponse(Schema):
    """Runtime capability flags the web reads to gate UI and flows.

    Single source of truth for whether a boundary flow is currently open, so the
    web consumes these instead of duplicating the server settings (which would
    drift). No secrets — only whether a gated flow is available.
    """

    shipping_checkout_available: bool
    payment_available: bool


@api.get("/capabilities", response=CapabilitiesResponse)
def capabilities(request: HttpRequest) -> CapabilitiesResponse:
    """Report which gated flows are open (see the settings behind each flag)."""
    del request
    return CapabilitiesResponse(
        shipping_checkout_available=settings.ENABLE_SHIPPING_CHECKOUT,
        payment_available=settings.ENABLE_MOCK_PAYMENT,
    )


# Import domain routers after the shared API exists; each module attaches its
# own Router to this singleton so OpenAPI stays in one document.
from apps.admin_rbac import api as admin_rbac_api  # noqa: E402,F401
from apps.cast import api as cast_api  # noqa: E402,F401
from apps.cheki import api as cheki_api  # noqa: E402,F401
from apps.commerce import api as commerce_api  # noqa: E402,F401
from apps.content import api as content_api  # noqa: E402,F401
from apps.coupon import api as coupon_api  # noqa: E402,F401
from apps.creator import api as creator_api  # noqa: E402,F401
from apps.dashboard import api as dashboard_api  # noqa: E402,F401
from apps.event_campaign import api as event_campaign_api  # noqa: E402,F401
from apps.identity import api as identity_api  # noqa: E402,F401
from apps.membership import api as membership_api  # noqa: E402,F401
from apps.notification import api as notification_api  # noqa: E402,F401
from apps.payments import api as payments_api  # noqa: E402,F401
from apps.pos_lite import api as pos_lite_api  # noqa: E402,F401
from apps.reservation import api as reservation_api  # noqa: E402,F401
from apps.safety import api as safety_api  # noqa: E402,F401
from apps.schedule import api as schedule_api  # noqa: E402,F401
from apps.social import api as social_api  # noqa: E402,F401
from apps.uploads import api as uploads_api  # noqa: E402,F401
from apps.visit import api as visit_api  # noqa: E402,F401
from apps.visit_guide import api as visit_guide_api  # noqa: E402,F401
