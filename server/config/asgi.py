"""ASGI entry point: HTTP via Django, WebSocket via Channels (ASS-240).

Defaults to dev settings; deployments set ``DJANGO_SETTINGS_MODULE``. Django is
initialised (``get_asgi_application``) *before* the Channels routing imports, so
the app registry is populated by the time consumers import domain models. HTTP
keeps flowing through the plain Django ASGI app (WSGI-equivalent request path);
only ``websocket`` connections take the Channels branch.

The websocket branch is wrapped, outermost-first, by
:class:`~channels.security.websocket.AllowedHostsOriginValidator` then
:class:`apps.identity.ws_auth.FanAuthMiddleware`: the ``Origin`` header is checked
against ``ALLOWED_HOSTS`` *before* authentication, so a cross-site page cannot open
an authenticated socket with a victim's cookie (CSWSH). A missing ``Origin`` (native
app / non-browser client) is allowed through to the auth layer, which then hard-gates
on the opaque token / access cookie (ADR-0002) before routing.
"""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

# Populate the app registry first; the imports below reach into domain models.
django_asgi_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from apps.identity.ws_auth import FanAuthMiddleware  # noqa: E402
from apps.notification.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_application,
        "websocket": AllowedHostsOriginValidator(
            FanAuthMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)
