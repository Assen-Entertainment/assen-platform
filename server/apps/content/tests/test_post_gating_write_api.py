"""Tests for the WRITE side of membership post gating (PostIn/PostPatch → entitlement).

The read side (``can_view_post`` / ``PostOut.locked`` redaction) is covered by
``test_post_entitlement_api``. Here we drive the *authoring* path: an owner creating or
editing a ``members`` post through the API sets ``visibility``/``required_tier``, and a
``required_tier`` must be one of the caller's own creator's tiers (else 422). We then read
the post back through the public API to assert the entitlement the write produced.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from django.test import Client

from apps.content.models import Post, PostVisibility
from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus

pytestmark = pytest.mark.django_db

POSTS = "/api/posts"
_SECRET_BODY = "비밀 본문"
_SECRET_MEDIA = "/media/secret.png"


def _bearer(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _fan(nickname: str = "팬") -> Account:
    return Account.objects.create(
        role=Role.FAN.value, nickname=nickname, kyc_status=KycStatus.VERIFIED.value
    )


def _owned_creator(handle: str = "stellar") -> tuple[Creator, Account]:
    """A creator plus the fan account that operates it (owner can author posts)."""
    owner = _fan(nickname="오너")
    creator = Creator.objects.create(handle=handle, name="별빛", owner=owner)
    return creator, owner


def _tier(creator: Creator, name: str = "스탠다드", price: int = 9900) -> MembershipTier:
    return MembershipTier.objects.create(creator=creator, name=name, price=price)


def _subscriber(creator: Creator, tier: MembershipTier | None = None) -> Account:
    """An active subscriber of ``creator`` (on ``tier`` if given, else a fresh tier)."""
    fan = _fan(nickname="구독자")
    Subscription.objects.create(
        fan=fan, tier=tier or _tier(creator), status=SubscriptionStatus.ACTIVE
    )
    return fan


def _post_json(client: Client, path: str, body: dict[str, Any], **extra: Any) -> Any:
    return client.post(
        path, data=json.dumps(body), content_type="application/json", **extra
    )


def _patch_json(client: Client, path: str, body: dict[str, Any], **extra: Any) -> Any:
    return client.patch(
        path, data=json.dumps(body), content_type="application/json", **extra
    )


def _create_members_post(
    client: Client, owner: Account, required_tier: MembershipTier | None = None
) -> str:
    """Author a ``members`` post as ``owner`` via the API; return its id."""
    body: dict[str, Any] = {
        "body": _SECRET_BODY,
        "media_url": _SECRET_MEDIA,
        "visibility": PostVisibility.MEMBERS.value,
    }
    if required_tier is not None:
        body["required_tier"] = str(required_tier.id)
    resp = _post_json(client, POSTS, body, headers=_bearer(owner))
    assert resp.status_code == 201, resp.content
    return str(resp.json()["id"])


def test_create_members_post_persists_visibility(client: Client) -> None:
    """Authoring visibility=members stores the gate (default public is unchanged)."""
    creator, owner = _owned_creator()
    post_id = _create_members_post(client, owner)
    post = Post.objects.get(id=post_id)
    assert post.visibility == PostVisibility.MEMBERS.value
    assert post.required_tier_id is None
    assert post.creator_id == creator.id


def test_members_post_locked_for_anonymous(client: Client) -> None:
    """A members post reads as a locked teaser (body/media redacted) to an anon viewer."""
    _creator, owner = _owned_creator()
    post_id = _create_members_post(client, owner)
    row = client.get(f"{POSTS}/{post_id}").json()
    assert row["locked"] is True
    assert row["body"] == ""
    assert row["media_url"] == ""


def test_members_post_unlocked_for_active_subscriber(client: Client) -> None:
    """An active subscriber (no required_tier) gets full content and locked=False."""
    creator, owner = _owned_creator()
    post_id = _create_members_post(client, owner)
    got = client.get(f"{POSTS}/{post_id}", headers=_bearer(_subscriber(creator)))
    body = got.json()
    assert body["locked"] is False
    assert body["body"] == _SECRET_BODY
    assert body["media_url"] == _SECRET_MEDIA


def test_members_post_with_required_tier_unlocks_matching_tier(client: Client) -> None:
    """required_tier gates to that exact tier: a matching subscriber sees it unlocked."""
    creator, owner = _owned_creator()
    gold = _tier(creator, name="골드", price=30000)
    post_id = _create_members_post(client, owner, required_tier=gold)
    got = client.get(f"{POSTS}/{post_id}", headers=_bearer(_subscriber(creator, gold)))
    body = got.json()
    assert body["locked"] is False
    assert body["body"] == _SECRET_BODY


def test_members_post_with_required_tier_locked_for_other_tier(client: Client) -> None:
    """A subscriber on a different tier than required_tier stays locked (exact match)."""
    creator, owner = _owned_creator()
    gold = _tier(creator, name="골드", price=30000)
    basic = _tier(creator, name="베이직", price=5000)
    post_id = _create_members_post(client, owner, required_tier=gold)
    row = client.get(f"{POSTS}/{post_id}", headers=_bearer(_subscriber(creator, basic)))
    body = row.json()
    assert body["locked"] is True
    assert body["body"] == ""


def test_create_members_post_rejects_foreign_tier(client: Client) -> None:
    """A required_tier owned by another creator is rejected 422 (no post created)."""
    _creator, owner = _owned_creator()
    other, _other_owner = _owned_creator(handle="other")
    foreign_tier = _tier(other, name="남의티어")
    resp = _post_json(
        client,
        POSTS,
        {
            "body": _SECRET_BODY,
            "visibility": PostVisibility.MEMBERS.value,
            "required_tier": str(foreign_tier.id),
        },
        headers=_bearer(owner),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "TierNotFound"
    assert Post.objects.count() == 0


def test_create_members_post_rejects_unknown_tier(client: Client) -> None:
    """A required_tier that does not exist is rejected 422 (no existence leak)."""
    _creator, owner = _owned_creator()
    resp = _post_json(
        client,
        POSTS,
        {
            "body": _SECRET_BODY,
            "visibility": PostVisibility.MEMBERS.value,
            "required_tier": str(uuid.uuid4()),
        },
        headers=_bearer(owner),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "TierNotFound"
    assert Post.objects.count() == 0


def test_create_public_post_ignores_required_tier(client: Client) -> None:
    """A required_tier on a public post is ignored (stored NULL, post stays open)."""
    creator, owner = _owned_creator()
    tier = _tier(creator)
    resp = _post_json(
        client,
        POSTS,
        {"body": "공개", "visibility": "public", "required_tier": str(tier.id)},
        headers=_bearer(owner),
    )
    assert resp.status_code == 201
    post = Post.objects.get(id=resp.json()["id"])
    assert post.visibility == PostVisibility.PUBLIC.value
    assert post.required_tier_id is None


def test_create_post_defaults_to_public(client: Client) -> None:
    """Omitting visibility keeps the backward-compatible public default (locked=False)."""
    _creator, owner = _owned_creator()
    resp = _post_json(client, POSTS, {"body": "안녕"}, headers=_bearer(owner))
    assert resp.status_code == 201
    assert resp.json()["locked"] is False
    assert Post.objects.get(id=resp.json()["id"]).visibility == PostVisibility.PUBLIC.value


def test_create_post_rejects_bad_visibility(client: Client) -> None:
    """An unknown visibility value fails schema validation (422)."""
    _creator, owner = _owned_creator()
    resp = _post_json(
        client, POSTS, {"body": "x", "visibility": "secret"}, headers=_bearer(owner)
    )
    assert resp.status_code == 422
    assert Post.objects.count() == 0


def test_update_public_post_to_members_locks(client: Client) -> None:
    """PATCH visibility=members locks a previously public post for a non-subscriber."""
    _creator, owner = _owned_creator()
    create = _post_json(
        client, POSTS, {"body": _SECRET_BODY}, headers=_bearer(owner)
    )
    post_id = create.json()["id"]
    patch = _patch_json(
        client,
        f"{POSTS}/{post_id}",
        {"visibility": PostVisibility.MEMBERS.value},
        headers=_bearer(owner),
    )
    assert patch.status_code == 200
    row = client.get(f"{POSTS}/{post_id}").json()
    assert row["locked"] is True
    assert row["body"] == ""


def test_update_members_post_to_public_clears_tier(client: Client) -> None:
    """PATCH visibility=public clears a prior required_tier and reopens the post."""
    creator, owner = _owned_creator()
    tier = _tier(creator)
    post_id = _create_members_post(client, owner, required_tier=tier)
    patch = _patch_json(
        client, f"{POSTS}/{post_id}", {"visibility": "public"}, headers=_bearer(owner)
    )
    assert patch.status_code == 200
    post = Post.objects.get(id=post_id)
    assert post.visibility == PostVisibility.PUBLIC.value
    assert post.required_tier_id is None
    assert client.get(f"{POSTS}/{post_id}").json()["locked"] is False


def test_update_post_rejects_foreign_required_tier(client: Client) -> None:
    """PATCH-ing a members post with another creator's tier is rejected 422."""
    _creator, owner = _owned_creator()
    other, _other_owner = _owned_creator(handle="other")
    foreign_tier = _tier(other, name="남의티어")
    post_id = _create_members_post(client, owner)
    patch = _patch_json(
        client,
        f"{POSTS}/{post_id}",
        {
            "visibility": PostVisibility.MEMBERS.value,
            "required_tier": str(foreign_tier.id),
        },
        headers=_bearer(owner),
    )
    assert patch.status_code == 422
    assert patch.json()["code"] == "TierNotFound"
    assert Post.objects.get(id=post_id).required_tier_id is None
