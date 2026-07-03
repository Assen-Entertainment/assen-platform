"""Tests for 19+ (adult_only) post gating (R3 gated features).

Fail-closed: with ENABLE_ADULT_CONTENT off an adult post is hidden from everyone;
with it on, only an adult_verified viewer sees it (list, single fetch, and feed).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client, override_settings

from apps.content.models import Post
from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _creator() -> Creator:
    return Creator.objects.create(handle="stellar", name="별빛")


def _verified_fan() -> Account:
    return Account.objects.create(
        role=Role.FAN.value, adult_verified=True, kyc_status=KycStatus.VERIFIED.value
    )


def _ids(resp: Any) -> set[str]:
    return {row["id"] for row in resp.json()["items"]}


@override_settings(ENABLE_ADULT_CONTENT=False)
def test_adult_post_hidden_from_everyone_when_flag_off(client: Client) -> None:
    creator = _creator()
    adult = Post.objects.create(creator=creator, body="성인 전용", adult_only=True)
    normal = Post.objects.create(creator=creator, body="일반", adult_only=False)
    verified = _verified_fan()

    anon_ids = _ids(client.get("/api/posts"))
    assert str(normal.id) in anon_ids
    assert str(adult.id) not in anon_ids
    # Even a verified fan sees no adult post while the flag is off (법무 사인 전).
    assert str(adult.id) not in _ids(client.get("/api/posts", headers=_auth(verified)))
    # Direct single fetch 404s (no existence leak) rather than exposing the post.
    assert (
        client.get(f"/api/posts/{adult.id}", headers=_auth(verified)).status_code == 404
    )


@override_settings(ENABLE_ADULT_CONTENT=True)
def test_adult_post_shown_only_to_verified_when_flag_on(client: Client) -> None:
    creator = _creator()
    adult = Post.objects.create(creator=creator, body="성인 전용", adult_only=True)
    verified = _verified_fan()
    unverified = Account.objects.create(role=Role.FAN.value)

    # Anonymous and unverified viewers still see nothing.
    assert str(adult.id) not in _ids(client.get("/api/posts"))
    assert str(adult.id) not in _ids(
        client.get("/api/posts", headers=_auth(unverified))
    )
    # A verified viewer sees it, flagged is_adult, on list and single fetch.
    assert str(adult.id) in _ids(client.get("/api/posts", headers=_auth(verified)))
    got = client.get(f"/api/posts/{adult.id}", headers=_auth(verified))
    assert got.status_code == 200
    assert got.json()["is_adult"] is True


@override_settings(ENABLE_ADULT_CONTENT=True)
def test_feed_applies_same_gate(client: Client) -> None:
    creator = _creator()
    adult = Post.objects.create(creator=creator, body="성인 전용", adult_only=True)
    verified = _verified_fan()
    assert str(adult.id) not in _ids(client.get("/api/feed"))
    assert str(adult.id) in _ids(client.get("/api/feed", headers=_auth(verified)))


def test_create_post_maps_is_adult_to_adult_only(client: Client) -> None:
    account = Account.objects.create(role=Role.FAN.value)
    Creator.objects.create(handle="mio", name="Mio", owner=account)

    def _post(body: dict[str, object], **extra: Any) -> Any:
        return client.post(
            "/api/posts",
            data=json.dumps(body),
            content_type="application/json",
            **extra,
        )

    res = _post({"body": "성인", "is_adult": True}, headers=_auth(account))
    assert res.status_code == 201
    post = Post.objects.get(id=res.json()["id"])
    assert post.adult_only is True
