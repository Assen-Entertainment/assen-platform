"""19+ (adult_only) gating for a post's *child* endpoints (Codex R3 BLOCKER #2).

Like/unlike, comment create, and comment list must apply the same 19+ gate as the
post read funnel, so a gated adult post cannot be read, probed, or mutated through
a child endpoint (404, no existence leak). Fail-closed: with the flag off nobody
sees it; with the flag on only an ``adult_verified`` viewer does.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client, override_settings

from apps.content.models import Comment, Like, Post
from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

JSON = "application/json"


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _creator() -> Creator:
    return Creator.objects.create(handle="stellar", name="별빛")


def _adult_post() -> Post:
    return Post.objects.create(creator=_creator(), body="성인 전용", adult_only=True)


def _verified_fan() -> Account:
    return Account.objects.create(
        role=Role.FAN.value, adult_verified=True, kyc_status=KycStatus.VERIFIED.value
    )


def _plain_fan() -> Account:
    return Account.objects.create(role=Role.FAN.value)


def _comment(client: Client, post_id: object, account: Account) -> Any:
    return client.post(
        f"/api/posts/{post_id}/comments",
        data=json.dumps({"body": "안녕"}),
        content_type=JSON,
        headers=_auth(account),
    )


# --- flag OFF: hidden from everyone (even a verified fan) --------------------- #


@override_settings(ENABLE_ADULT_CONTENT=False)
def test_like_on_adult_post_404_when_flag_off(client: Client) -> None:
    post = _adult_post()
    res = client.put(f"/api/posts/{post.id}/like", headers=_auth(_verified_fan()))
    assert res.status_code == 404
    assert not Like.objects.filter(post=post).exists()


@override_settings(ENABLE_ADULT_CONTENT=False)
def test_unlike_on_adult_post_404_when_flag_off(client: Client) -> None:
    post = _adult_post()
    res = client.delete(f"/api/posts/{post.id}/like", headers=_auth(_verified_fan()))
    assert res.status_code == 404


@override_settings(ENABLE_ADULT_CONTENT=False)
def test_comment_create_on_adult_post_404_when_flag_off(client: Client) -> None:
    post = _adult_post()
    res = _comment(client, post.id, _verified_fan())
    assert res.status_code == 404
    assert not Comment.objects.filter(post=post).exists()


@override_settings(ENABLE_ADULT_CONTENT=False)
def test_comment_list_on_adult_post_404_when_flag_off(client: Client) -> None:
    post = _adult_post()
    Comment.objects.create(post=post, author_name="비밀", body="숨은 댓글")
    # Anonymous and even a verified fan see 404 while the flag is off.
    assert client.get(f"/api/posts/{post.id}/comments").status_code == 404
    assert (
        client.get(
            f"/api/posts/{post.id}/comments", headers=_auth(_verified_fan())
        ).status_code
        == 404
    )


# --- flag ON: verified passes, unverified/anonymous 404 ---------------------- #


@override_settings(ENABLE_ADULT_CONTENT=True)
def test_child_endpoints_ok_for_verified_when_flag_on(client: Client) -> None:
    post = _adult_post()
    fan = _verified_fan()
    assert client.put(f"/api/posts/{post.id}/like", headers=_auth(fan)).status_code == 200
    assert _comment(client, post.id, fan).status_code == 201
    assert (
        client.get(f"/api/posts/{post.id}/comments", headers=_auth(fan)).status_code == 200
    )


@override_settings(ENABLE_ADULT_CONTENT=True)
def test_child_endpoints_404_for_unverified_when_flag_on(client: Client) -> None:
    post = _adult_post()
    fan = _plain_fan()  # authenticated but not adult_verified
    assert client.put(f"/api/posts/{post.id}/like", headers=_auth(fan)).status_code == 404
    assert _comment(client, post.id, fan).status_code == 404
    assert (
        client.get(f"/api/posts/{post.id}/comments", headers=_auth(fan)).status_code == 404
    )
    assert not Like.objects.filter(post=post).exists()
    assert not Comment.objects.filter(post=post).exists()


# --- non-adult posts are unaffected (no over-gating regression) --------------- #


def test_child_endpoints_ok_on_normal_post(client: Client) -> None:
    post = Post.objects.create(creator=_creator(), body="일반")
    fan = _plain_fan()
    assert client.put(f"/api/posts/{post.id}/like", headers=_auth(fan)).status_code == 200
    assert _comment(client, post.id, fan).status_code == 201
    assert client.get(f"/api/posts/{post.id}/comments").status_code == 200
