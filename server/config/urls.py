"""Root URL configuration.

Mounts the Django admin and the single Ninja API instance (config.api). Domain
routers attach to that NinjaAPI from inside each app's api.py (CONSTRAINTS #38).
"""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path

from config.api import api


def healthz(_request: HttpRequest) -> HttpResponse:
    """Return a bare 200 for infrastructure liveness probes.

    Distinct from the richer JSON `/api/health` endpoint: load balancers only
    need a cheap, dependency-free signal that the process is up.
    """
    return HttpResponse("ok")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("healthz", healthz),
]
