"""Tests for the public creator-followers list endpoint.

`GET /api/creators/{handle}/followers` — a public, keyset-paginated list of a
creator's followers exposing only already-public display identity (nickname, and
a profile link when the follower is themselves a creator). Withdrawn accounts are
excluded; an unknown handle 404s.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.social.models import Follow

pytestmark = pytest.mark.django_db

BASE = "/api/creators"


def _creator(handle: str, name: str = "크리에이터", **extra: object) -> Creator:
    """Create a creator with the given handle."""
    return Creator.objects.create(handle=handle, name=name, **extra)


def _fan(nickname: str, *, is_active: bool = True) -> Account:
    """Create a plain fan account with a display nickname."""
    return Account.objects.create(
        role=Role.FAN.value, nickname=nickname, is_active=is_active
    )


def test_unknown_handle_404(client: Client) -> None:
    """An unknown creator handle returns 404 (no existence leak)."""
    assert client.get(f"{BASE}/nope/followers").status_code == 404


def test_empty_followers(client: Client) -> None:
    """A creator with no followers returns an empty page, no cursor."""
    _creator("stellar")
    body = client.get(f"{BASE}/stellar/followers").json()
    assert body == {"items": [], "next_cursor": None}


def test_lists_follower_nicknames(client: Client) -> None:
    """Followers are listed by their public nickname; a plain fan is not a creator."""
    creator = _creator("stellar")
    Follow.objects.create(follower=_fan("민지"), creator=creator)
    Follow.objects.create(follower=_fan("지수"), creator=creator)

    body = client.get(f"{BASE}/stellar/followers").json()

    assert {row["nickname"] for row in body["items"]} == {"민지", "지수"}
    assert all(row["is_creator"] is False for row in body["items"])
    assert all(row["handle"] == "" for row in body["items"])
    assert body["next_cursor"] is None


def test_creator_follower_carries_profile_link(client: Client) -> None:
    """A follower who operates a creator exposes their handle + avatar for linking."""
    target = _creator("stellar")
    fan_creator_account = _fan("루나")
    _creator(
        "luna", name="루나", owner=fan_creator_account, avatar_url="https://x/a.png"
    )
    Follow.objects.create(follower=fan_creator_account, creator=target)

    row = client.get(f"{BASE}/stellar/followers").json()["items"][0]

    assert row["nickname"] == "루나"
    assert row["is_creator"] is True
    assert row["handle"] == "luna"
    assert row["avatar_url"] == "https://x/a.png"


def test_withdrawn_followers_excluded(client: Client) -> None:
    """A withdrawn (deactivated) follower is not surfaced in the list."""
    creator = _creator("stellar")
    Follow.objects.create(follower=_fan("활성"), creator=creator)
    Follow.objects.create(
        follower=_fan("탈퇴", is_active=False), creator=creator
    )

    body = client.get(f"{BASE}/stellar/followers").json()

    assert {row["nickname"] for row in body["items"]} == {"활성"}


def test_pagination_walks_all_followers(client: Client) -> None:
    """A limit-bounded page yields a cursor; the walk covers every follower once."""
    creator = _creator("stellar")
    for i in range(3):
        Follow.objects.create(follower=_fan(f"fan-{i}"), creator=creator)

    first = client.get(f"{BASE}/stellar/followers?limit=2").json()
    assert len(first["items"]) == 2
    assert first["next_cursor"] is not None

    cursor = first["next_cursor"]
    second = client.get(f"{BASE}/stellar/followers?limit=2&cursor={cursor}").json()
    assert len(second["items"]) == 1
    assert second["next_cursor"] is None

    seen = {row["nickname"] for row in first["items"] + second["items"]}
    assert seen == {"fan-0", "fan-1", "fan-2"}
