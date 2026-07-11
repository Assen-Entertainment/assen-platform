"""Realtime notification WebSocket consumer (ASS-240).

The web/app fan surface opens one socket per authenticated fan. On connect the
consumer requires ``scope["account"]`` (injected by
:class:`apps.identity.ws_auth.FanAuthMiddleware`); an anonymous/invalid socket is
closed with 4401. An authenticated fan joins the group carrying only their own
notifications and is sent their current unread count once, so the web badge is
correct the instant the socket opens. A notification created anywhere in the
domain reaches this socket because :func:`apps.notification.services.notify`
fans out to the same group (see :func:`apps.notification.services.account_group_name`).

Handshake auth is not enough on its own: a long-lived socket must still honour a
token revoked (logout / refresh-reuse) or expired *after* connect (F11, ASS-292).
So before every outbound delivery the consumer re-runs the single fan gate
(:func:`apps.identity.services.verify_access_token`) on the raw token stashed at
``scope["access_token"]``; a token that no longer resolves closes the socket with
4401 instead of forwarding, leaving no window where a revoked socket keeps
receiving. The token is never logged.

Chat/DM, presence, and live are intentionally out of scope — this lays the
realtime rail; those surfaces mount their own consumers later.
"""

from __future__ import annotations

from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.identity.models import Account
from apps.identity.services import TokenError, verify_access_token
from apps.notification.models import Notification
from apps.notification.services import account_group_name

# Close code for an unauthenticated connection (application-defined, 4000–4999).
WS_CLOSE_UNAUTHENTICATED = 4401


def _unread_count(account: Account) -> int:
    """Return the account's current unread-notification count."""
    return Notification.objects.filter(recipient=account, read_at__isnull=True).count()


def _token_still_authorized(token: str) -> bool:
    """True if the presented access token still resolves to an account (ASS-292).

    Re-runs the one fan gate (:func:`verify_access_token`) so a token whose family
    was revoked (logout / refresh-reuse) or whose expiry has passed is rejected on
    the live socket, not only at the handshake. Never logs the token.
    """
    try:
        verify_access_token(token)
    except TokenError:
        return False
    return True


class NotificationConsumer(AsyncJsonWebsocketConsumer):  # type: ignore[misc]
    """Per-fan realtime notification socket (path ``ws/notifications``)."""

    async def connect(self) -> None:
        """Authenticate, join the account's group, and send the unread count."""
        account: Account | None = self.scope.get("account")
        if account is None:
            await self.close(code=WS_CLOSE_UNAUTHENTICATED)
            return
        self.group_name: str = account_group_name(account.pk)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        unread = await database_sync_to_async(_unread_count)(account)
        await self.send_json({"type": "unread_count", "count": unread})

    async def disconnect(self, code: int) -> None:
        """Leave the account's group (no-op if the socket was never accepted)."""
        group_name: str | None = getattr(self, "group_name", None)
        if group_name is not None:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def notify_message(self, event: dict[str, Any]) -> None:
        """Forward a group-sent notification payload to the client.

        Handles the ``notify.message`` group event emitted by
        :func:`apps.notification.services.notify`. Before forwarding, the token
        presented at connect is re-verified: if it was revoked/expired since the
        handshake the socket is closed with 4401 instead of delivering (ASS-292),
        so a stale socket cannot keep receiving.
        """
        token: str | None = self.scope.get("access_token")
        if token is None or not await database_sync_to_async(_token_still_authorized)(token):
            await self.close(code=WS_CLOSE_UNAUTHENTICATED)
            return
        await self.send_json({"type": "notification", "notification": event["notification"]})
