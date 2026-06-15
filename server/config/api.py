"""Single Ninja API instance for Assen Platform (ADR-0001, CONSTRAINTS #15).

Domain apps register their routers on this instance from their own api.py
modules. The schema this produces is the source for the Dart client codegen
pipeline (swagger_parser) in P6.
"""

from __future__ import annotations

import os
import subprocess

from django.http import HttpRequest
from ninja import NinjaAPI, Schema

api = NinjaAPI(title="Assen Platform API", version="0.1.0")


class HealthResponse(Schema):
    """Health payload returned by the `/api/health` endpoint."""

    status: str
    version: str
    commit: str


def _git_commit() -> str:
    """Return the current git commit hash, or "unknown" if unavailable.

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
        commit=_git_commit(),
    )


# Import domain routers after the shared API exists; each module attaches its
# own Router to this singleton so OpenAPI stays in one document.
from apps.cheki import api as cheki_api  # noqa: E402,F401
from apps.dashboard import api as dashboard_api  # noqa: E402,F401
from apps.identity import api as identity_api  # noqa: E402,F401
from apps.safety import api as safety_api  # noqa: E402,F401
from apps.schedule import api as schedule_api  # noqa: E402,F401
from apps.visit import api as visit_api  # noqa: E402,F401
