"""ASGI entry point: HTTP via Django, WebSocket via Channels (ASS-240).

Defaults to dev settings; deployments set ``DJANGO_SETTINGS_MODULE``. Django is
initialised (``get_asgi_application``) *before* the Channels routing imports, so
the app registry is populated by the time consumers import domain models. HTTP
keeps flowing through the plain Django ASGI app (WSGI-equivalent request path);
only ``websocket`` connections take the Channels branch, authenticated by
:class:`apps.identity.ws_auth.FanAuthMiddleware` (opaque token / access cookie,
ADR-0002) before routing.
"""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

# Populate the app registry first; the imports below reach into domain models.
django_asgi_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from apps.identity.ws_auth import FanAuthMiddleware  # noqa: E402
from apps.notification.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_application,
        "websocket": FanAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
