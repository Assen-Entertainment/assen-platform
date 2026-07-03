"""Tests for the in-app notification feed + notify() service (E11/B4)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.notification.models import Notification, NotificationKind
from apps.notification.services import notify

pytestmark = pytest.mark.django_db

BASE = "/api/notifications"


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    """Return a test-client headers mapping bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def test_notify_creates_feed_row() -> None:
    """The notify() service appends one unread notification for the recipient."""
    fan = _fan()
    created = notify(
        fan, NotificationKind.FOLLOW.value, "새 팔로워가 생겼어요.", "/creator/stellar"
    )
    assert created.read_at is None
    assert Notification.objects.filter(recipient=fan).count() == 1


def test_list_newest_first_and_scoped(client: Client) -> None:
    """The feed lists the fan's own notifications newest first (cursor shape)."""
    fan = _fan()
    other = _fan()
    older = notify(fan, NotificationKind.LIKE.value, "첫 번째")
    newer = notify(fan, NotificationKind.COMMENT.value, "두 번째")
    notify(other, NotificationKind.SYSTEM.value, "남의 것")
    # Space the timestamps so "newest first" is deterministic (rapid creates on
    # a coarse-resolution clock can otherwise tie on created_at).
    now = timezone.now()
    Notification.objects.filter(id=older.id).update(created_at=now - timedelta(minutes=2))
    Notification.objects.filter(id=newer.id).update(created_at=now - timedelta(minutes=1))

    body = client.get(BASE, headers=_auth(fan)).json()
    titles = [n["title"] for n in body["items"]]
    assert titles == ["두 번째", "첫 번째"]
    assert "next_cursor" in body
    assert all(n["read"] is False for n in body["items"])


def test_mark_one_read(client: Client) -> None:
    """Marking one notification read flips its read flag."""
    fan = _fan()
    n = notify(fan, NotificationKind.ORDER.value, "주문 접수")
    res = client.post(f"{BASE}/{n.id}/read", headers=_auth(fan))
    assert res.status_code == 200
    assert res.json()["read"] is True
    assert Notification.objects.get(id=n.id).read_at is not None


def test_mark_read_another_fans_is_404(client: Client) -> None:
    """Marking someone else's notification read is a 404 (no existence leak)."""
    owner = _fan()
    other = _fan()
    n = notify(owner, NotificationKind.SYSTEM.value, "공지")
    res = client.post(f"{BASE}/{n.id}/read", headers=_auth(other))
    assert res.status_code == 404


def test_read_all(client: Client) -> None:
    """read-all marks every unread notification read and reports the count."""
    fan = _fan()
    notify(fan, NotificationKind.LIKE.value, "a")
    notify(fan, NotificationKind.LIKE.value, "b")
    already = notify(fan, NotificationKind.LIKE.value, "c")
    client.post(f"{BASE}/{already.id}/read", headers=_auth(fan))

    res = client.post(f"{BASE}/read-all", headers=_auth(fan))
    assert res.status_code == 200
    assert res.json()["updated"] == 2  # only the two still-unread ones
    assert not Notification.objects.filter(recipient=fan, read_at__isnull=True).exists()


def test_feed_requires_auth(client: Client) -> None:
    """An anonymous caller cannot read the notification feed."""
    assert client.get(BASE).status_code == 401
