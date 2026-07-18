"""Root URL configuration.

Mounts the Django admin and the single Ninja API instance (config.api). Domain
routers attach to that NinjaAPI from inside each app's api.py (CONSTRAINTS #38).
"""

from __future__ import annotations

from django.contrib import admin
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import path, re_path

from apps.uploads.media import serve_upload
from config.api import api
from config.observability import git_sha


def healthz(_request: HttpRequest) -> HttpResponse:
    """Return a bare 200 for infrastructure liveness probes.

    Distinct from the richer JSON `/api/health` endpoint: load balancers only
    need a cheap, dependency-free signal that the process is up.
    """
    return HttpResponse("ok")


def readyz(_request: HttpRequest) -> JsonResponse:
    """Readiness probe: 200 only when the process can serve real traffic.

    Unlike liveness (`/healthz`), readiness checks the dependencies a request
    actually needs — here, the database connection. Returns 503 with the failing
    check named so an orchestrator drains the task instead of routing to it. Also
    surfaces the running version/commit (env `GIT_SHA`) for deploy verification.
    No auth, no DB writes; redirect-exempt in prod like `/healthz`.
    """
    checks: dict[str, str] = {}
    try:
        connection.ensure_connection()
    except Exception:  # broad by design: any DB failure means "not ready", never a 500
        checks["database"] = "error"
    else:
        checks["database"] = "ok"

    ready = all(status == "ok" for status in checks.values())
    payload = {
        "status": "ready" if ready else "not ready",
        "checks": checks,
        "version": api.version,
        "commit": git_sha(),
    }
    return JsonResponse(payload, status=200 if ready else 503)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("healthz", healthz),
    path("readyz", readyz),
    # User-uploaded media, served by Django on EVERY backend and in EVERY environment
    # (대표 approved 07-18) — local filesystem in dev/test/demo, S3 in production. The
    # view reads through ``default_storage``, so the route does not vary with the
    # backend and neither does the URL it serves.
    #
    # Unconditional, and NOT gated on DEBUG: proxying reads is what makes a media URL
    # stable (a bucket-direct read needs a signed URL, which expires — and this one is
    # persisted) and what makes a moderation takedown immediate (the view checks the
    # Upload row; a bucket-direct read never reaches Django, so nothing could check).
    # Django's ``static()`` helper is unusable for the same DEBUG reason it always was:
    # it returns [] unless DEBUG, and demo/prod run with DEBUG off.
    #
    # Responses also pass through SecurityMiddleware / SecurityHeadersMiddleware, which
    # stamp X-Content-Type-Options: nosniff globally, so the row-pinned content-type
    # cannot be re-sniffed by the browser (the view sets it explicitly too).
    re_path(r"^media/(?P<path>.*)$", serve_upload),
]
