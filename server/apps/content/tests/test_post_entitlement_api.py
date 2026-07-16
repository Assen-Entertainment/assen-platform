"""API-level membership entitlement — locked flag + body/media redaction (Codex #10).

The list and detail endpoints redact a ``members`` post's body/media (to "") and
set ``locked=True`` for a non-entitled viewer, while an entitled active subscriber
gets the full content and ``locked=False``. Independent of the 19+ gate (these
posts are not adult, so they pass the adult filter regardless).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from apps.content.models import Post, PostVisibility
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus

pytestmark = pytest.mark.django_db

POSTS = "/api/posts"
_SECRET_BODY = "비밀 본문"
_SECRET_MEDIA = "/media/secret.png"


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _fan() -> Account:
    return Account.objects.create(role=Role.FAN.value)


def _gated_post(creator: Creator) -> Post:
    return Post.objects.create(
        creator=creator,
        body=_SECRET_BODY,
        media_url=_SECRET_MEDIA,
        visibility=PostVisibility.MEMBERS.value,
    )


def _subscriber(creator: Creator) -> Account:
    tier = MembershipTier.objects.create(creator=creator, name="스탠다드", price=9900)
    fan = _fan()
    Subscription.objects.create(fan=fan, tier=tier, status=SubscriptionStatus.ACTIVE)
    return fan


def _row(resp: Any, post_id: str) -> dict[str, Any]:
    return next(row for row in resp.json()["items"] if row["id"] == post_id)


def test_list_redacts_gated_post_for_non_entitled(client: Client) -> None:
    """The list shows a gated post as a locked teaser with body/media redacted."""
    post = _gated_post(Creator.objects.create(handle="stellar", name="별빛"))
    row = _row(client.get(POSTS), str(post.id))
    assert row["locked"] is True
    assert row["body"] == ""
    assert row["media_url"] == ""


def test_detail_redacts_gated_post_for_non_entitled(client: Client) -> None:
    """The detail endpoint redacts a gated post for a non-entitled viewer."""
    post = _gated_post(Creator.objects.create(handle="stellar", name="별빛"))
    body = client.get(f"{POSTS}/{post.id}").json()
    assert body["locked"] is True
    assert body["body"] == ""
    assert body["media_url"] == ""


def test_list_full_content_for_entitled_subscriber(client: Client) -> None:
    """An active subscriber gets full content and locked=False in the list."""
    creator = Creator.objects.create(handle="stellar", name="별빛")
    post = _gated_post(creator)
    row = _row(client.get(POSTS, headers=_auth(_subscriber(creator))), str(post.id))
    assert row["locked"] is False
    assert row["body"] == _SECRET_BODY
    assert row["media_url"] == _SECRET_MEDIA


def test_detail_full_content_for_entitled_subscriber(client: Client) -> None:
    """An active subscriber gets full content and locked=False on detail."""
    creator = Creator.objects.create(handle="stellar", name="별빛")
    post = _gated_post(creator)
    got = client.get(f"{POSTS}/{post.id}", headers=_auth(_subscriber(creator)))
    assert got.status_code == 200
    body = got.json()
    assert body["locked"] is False
    assert body["body"] == _SECRET_BODY
    assert body["media_url"] == _SECRET_MEDIA


def test_public_post_never_locked(client: Client) -> None:
    """A public post is returned in full to an anonymous viewer (locked=False)."""
    creator = Creator.objects.create(handle="stellar", name="별빛")
    post = Post.objects.create(creator=creator, body="공개", media_url="/media/open.png")
    row = _row(client.get(POSTS), str(post.id))
    assert row["locked"] is False
    assert row["body"] == "공개"
    assert row["media_url"] == "/media/open.png"
