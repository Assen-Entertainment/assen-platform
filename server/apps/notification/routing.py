"""WebSocket URL routing for the realtime surface (ASS-240).

Mounted under the ``websocket`` protocol in :mod:`config.asgi`. Only the
notification socket exists today; chat/DM, presence, and live add their patterns
here as they land.
"""

from __future__ import annotations

from django.urls import path

from apps.notification.consumers import NotificationConsumer

websocket_urlpatterns = [
    path("ws/notifications", NotificationConsumer.as_asgi()),
]
