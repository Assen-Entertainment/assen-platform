"""Root URL configuration.

Mounts the Django admin and the single Ninja API instance (config.api). Domain
routers attach to that NinjaAPI from inside each app's api.py (CONSTRAINTS #38).
"""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import path

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
]

# dev-only: serve user-uploaded media from the local filesystem so the feed/catalog
# can render freshly uploaded images without a CDN. ``static()`` returns [] unless
# DEBUG, so this is a no-op in prod (where S3/CDN serves MEDIA_URL) — media is never
# served through Django in production.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
