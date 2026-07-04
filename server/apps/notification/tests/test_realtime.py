"""Realtime notification WebSocket tests (ASS-240).

Exercises the Channels stack over the in-memory channel layer:
- an authenticated fan connects, joins their group, and receives their unread
  count on connect;
- :func:`~apps.notification.services.notify` fans a new row out to the group;
- a message on the group is forwarded to the open socket;
- an unauthenticated connection is rejected (close 4401);
- a channel-layer failure never breaks the durable feed write (best-effort).

The notify()->socket path is split into two tests on purpose: the in-memory
channel layer binds its queues to one event loop, but notify() (sync domain code)
must reach the layer through ``async_to_sync`` on a worker thread — a different
loop. So one test asserts notify() calls the layer with the right group+payload,
and another asserts the consumer forwards a group message to the client; together
they cover the end-to-end contract without cross-loop flakiness. DB-touching async
tests use ``transaction=True`` so committed rows are visible to the consumer's and
middleware's threaded ORM reads.
"""

from __future__ import annotations

from unittest import mock

import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.identity.ws_auth import FanAuthMiddleware
from apps.notification.models import Notification, NotificationKind
from apps.notification.routing import websocket_urlpatterns
from apps.notification.services import notify

WS_PATH = "/ws/notifications"


def _ws_application() -> FanAuthMiddleware:
    """Build the production WebSocket stack (auth middleware wrapping the router)."""
    return FanAuthMiddleware(URLRouter(websocket_urlpatterns))


def _bearer_headers(access_token: str) -> list[tuple[bytes, bytes]]:
    """ASGI header list carrying the fan bearer token."""
    return [(b"authorization", f"Bearer {access_token}".encode())]


def _make_fan_with_token() -> tuple[Account, str]:
    """Create a fan and issue an access token (committed for cross-thread reads)."""
    account = Account.objects.create(role=Role.FAN.value)
    token = issue_token_pair(account).access_token
    return account, token


def _seed_unread(account: Account, count: int) -> None:
    """Append ``count`` unread notifications to the account's feed."""
    for i in range(count):
        Notification.objects.create(
            recipient=account, kind=NotificationKind.SYSTEM.value, title=f"n{i}"
        )


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_authed_connect_receives_unread_count() -> None:
    """An authenticated fan connects, joins the group, and gets the unread count."""
    account, token = await database_sync_to_async(_make_fan_with_token)()
    await database_sync_to_async(_seed_unread)(account, 3)
    communicator = WebsocketCommunicator(
        _ws_application(), WS_PATH, headers=_bearer_headers(token)
    )
    connected, _ = await communicator.connect()
    assert connected is True
    message = await communicator.receive_json_from()
    assert message == {"type": "unread_count", "count": 3}
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_unauthenticated_connect_is_rejected() -> None:
    """A connection with no credentials is closed with 4401 (no group joined)."""
    communicator = WebsocketCommunicator(_ws_application(), WS_PATH)
    connected, code = await communicator.connect()
    assert connected is False
    assert code == 4401


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_group_message_is_forwarded_to_the_socket() -> None:
    """A message on the account's group is delivered to the open socket."""
    account, token = await database_sync_to_async(_make_fan_with_token)()
    communicator = WebsocketCommunicator(
        _ws_application(), WS_PATH, headers=_bearer_headers(token)
    )
    connected, _ = await communicator.connect()
    assert connected is True
    await communicator.receive_json_from()  # drain the connect-time unread count

    notification = {
        "id": "3f8b",
        "kind": NotificationKind.FOLLOW.value,
        "title": "새 팔로워가 생겼어요.",
        "href": "/creator/stellar",
        "created_at": "2026-07-04T00:00:00+00:00",
    }
    layer = get_channel_layer()
    await layer.group_send(
        f"notifications_{account.pk}",
        {"type": "notify.message", "notification": notification},
    )
    message = await communicator.receive_json_from()
    assert message == {"type": "notification", "notification": notification}
    await communicator.disconnect()


@pytest.mark.django_db
def test_notify_fans_out_to_the_recipients_group() -> None:
    """notify() best-effort pushes the new row to the recipient's group."""
    account = Account.objects.create(role=Role.FAN.value)
    layer = mock.Mock()
    layer.group_send = mock.AsyncMock()  # async_to_sync needs an awaitable callable
    with mock.patch("channels.layers.get_channel_layer", return_value=layer):
        created = notify(account, NotificationKind.COMMENT.value, "새 댓글이 달렸어요.", "/p/1")

    layer.group_send.assert_called_once()
    group, payload = layer.group_send.call_args.args
    assert group == f"notifications_{account.pk}"
    assert payload["type"] == "notify.message"
    assert payload["notification"] == {
        "id": str(created.id),
        "kind": NotificationKind.COMMENT.value,
        "title": "새 댓글이 달렸어요.",
        "href": "/p/1",
        "created_at": created.created_at.isoformat(),
    }


@pytest.mark.django_db
def test_channel_layer_failure_does_not_break_feed_write() -> None:
    """A group_send failure is swallowed; the durable feed row is still created."""
    account = Account.objects.create(role=Role.FAN.value)
    layer = mock.Mock()
    layer.group_send = mock.AsyncMock(side_effect=RuntimeError("channel layer down"))
    with mock.patch("channels.layers.get_channel_layer", return_value=layer):
        created = notify(account, NotificationKind.LIKE.value, "좋아요를 받았어요.")

    assert Notification.objects.filter(id=created.id).count() == 1
    assert created.read_at is None
