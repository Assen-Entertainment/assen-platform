"""Tests for the content read API — posts, feed, comments (E11/B2)."""

from __future__ import annotations

import uuid

import pytest
from django.apps import apps
from django.test import Client

from apps.content.models import Comment, Like, Post
from apps.creator.models import Creator
from apps.identity.models import Account, Role

pytestmark = pytest.mark.django_db

POSTS = "/api/posts"
FEED = "/api/feed"


def _creator(handle: str = "stellar") -> Creator:
    """Create a creator."""
    return Creator.objects.create(handle=handle, name="별빛", verified=True)


def test_content_app_installed() -> None:
    """The content app is registered."""
    assert apps.is_installed("apps.content")


def test_list_posts_and_creator_filter(client: Client) -> None:
    """Listing returns all posts; ``?creator_id=`` scopes to one creator."""
    c1 = _creator("stellar")
    c2 = _creator("rabbit")
    Post.objects.create(creator=c1, body="hi")
    Post.objects.create(creator=c2, body="yo")
    everything = client.get(POSTS).json()
    assert len(everything["items"]) == 2
    scoped = client.get(f"{POSTS}?creator_id={c1.id}").json()
    assert len(scoped["items"]) == 1
    assert scoped["items"][0]["creator_handle"] == "stellar"
    assert scoped["items"][0]["verified"] is True


def test_post_detail_and_404(client: Client) -> None:
    """A known post returns 200; an unknown id returns 404."""
    post = Post.objects.create(creator=_creator(), body="hello")
    ok = client.get(f"{POSTS}/{post.id}")
    assert ok.status_code == 200
    assert ok.json()["body"] == "hello"
    assert client.get(f"{POSTS}/{uuid.uuid4()}").status_code == 404


def test_like_and_comment_counts(client: Client) -> None:
    """Like/comment counts are derived from the relations."""
    post = Post.objects.create(creator=_creator(), body="x")
    fan = Account.objects.create(role=Role.FAN.value)
    Like.objects.create(post=post, user=fan)
    Comment.objects.create(post=post, author_name="팬", body="좋아요")
    body = client.get(f"{POSTS}/{post.id}").json()
    assert body["like_count"] == 1
    assert body["comment_count"] == 1


def test_comments_endpoint_and_404(client: Client) -> None:
    """Comments list returns the post's comments; unknown post is 404."""
    post = Post.objects.create(creator=_creator(), body="x")
    Comment.objects.create(post=post, author_name="팬 하나", body="응원해요")
    listed = client.get(f"{POSTS}/{post.id}/comments").json()
    assert len(listed["items"]) == 1
    assert listed["items"][0]["author"] == "팬 하나"
    assert listed["items"][0]["body"] == "응원해요"
    missing = client.get(f"{POSTS}/{uuid.uuid4()}/comments")
    assert missing.status_code == 404


def test_comment_never_leaks_fan_id(client: Client) -> None:
    """An authored comment renders the display nickname, never the internal fan_id."""
    post = Post.objects.create(creator=_creator(), body="x")
    author = Account.objects.create(role=Role.FAN.value, nickname="닉네임")
    Comment.objects.create(post=post, author=author, author_name="", body="hi")
    row = client.get(f"{POSTS}/{post.id}/comments").json()["items"][0]
    assert row["author"] == "닉네임"
    assert str(author.fan_id) not in row["author"]


def test_comment_anonymous_author_falls_back(client: Client) -> None:
    """A comment with no author and no display name falls back to 익명."""
    post = Post.objects.create(creator=_creator(), body="x")
    Comment.objects.create(post=post, author=None, author_name="", body="hi")
    row = client.get(f"{POSTS}/{post.id}/comments").json()["items"][0]
    assert row["author"] == "익명"


def test_feed_returns_recent_posts(client: Client) -> None:
    """The anonymous feed returns recent posts across creators."""
    Post.objects.create(creator=_creator("stellar"), body="a")
    Post.objects.create(creator=_creator("rabbit"), body="b")
    body = client.get(FEED).json()
    assert len(body["items"]) == 2
