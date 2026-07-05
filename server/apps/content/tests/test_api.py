"""Tests for the content read + write API — posts, feed, comments, likes (E11/B2+B4)."""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from django.apps import apps
from django.test import Client

from apps.content.models import Comment, Like, Post
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

POSTS = "/api/posts"
FEED = "/api/feed"


def _creator(handle: str = "stellar") -> Creator:
    """Create a creator."""
    return Creator.objects.create(handle=handle, name="별빛", verified=True)


def _fan(nickname: str = "미오팬") -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value, nickname=nickname)


def _bearer(account: Account) -> dict[str, str]:
    """Authorization header carrying a freshly issued access token for ``account``."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _post_json(client: Client, path: str, body: dict[str, Any], **extra: Any) -> Any:
    """POST a JSON body (Ninja parses application/json request bodies)."""
    return client.post(
        path, data=json.dumps(body), content_type="application/json", **extra
    )


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


# --- like / unlike -----------------------------------------------------------


def test_like_and_unlike_toggle(client: Client) -> None:
    """PUT likes (idempotent), DELETE unlikes; the fresh count is returned."""
    post = Post.objects.create(creator=_creator(), body="x")
    fan = _fan()
    headers = _bearer(fan)
    url = f"{POSTS}/{post.id}/like"

    liked = client.put(url, headers=headers)
    assert liked.status_code == 200
    assert liked.json() == {"liked": True, "like_count": 1}
    # Idempotent: a second like does not double-count.
    again = client.put(url, headers=headers)
    assert again.json() == {"liked": True, "like_count": 1}
    assert Like.objects.filter(post=post, user=fan).count() == 1

    unliked = client.delete(url, headers=headers)
    assert unliked.status_code == 200
    assert unliked.json() == {"liked": False, "like_count": 0}
    assert not Like.objects.filter(post=post, user=fan).exists()


def test_like_requires_auth(client: Client) -> None:
    """An unauthenticated like is rejected; no like row is created."""
    post = Post.objects.create(creator=_creator(), body="x")
    resp = client.put(f"{POSTS}/{post.id}/like")
    assert resp.status_code in {401, 403}
    assert Like.objects.count() == 0


def test_like_unknown_post_is_404(client: Client) -> None:
    """Liking an unknown post returns 404."""
    resp = client.put(f"{POSTS}/{uuid.uuid4()}/like", headers=_bearer(_fan()))
    assert resp.status_code == 404


# --- comment create ----------------------------------------------------------


def test_create_comment_records_author_and_nickname(client: Client) -> None:
    """A created comment is authored by the fan and renders their nickname."""
    post = Post.objects.create(creator=_creator(), body="x")
    fan = _fan(nickname="응원단장")
    resp = _post_json(
        client, f"{POSTS}/{post.id}/comments", {"body": "화이팅"}, headers=_bearer(fan)
    )
    assert resp.status_code == 201
    row = resp.json()
    assert row["author"] == "응원단장"
    assert row["body"] == "화이팅"
    assert row["post_id"] == str(post.id)
    comment = Comment.objects.get(id=row["id"])
    assert comment.author_id == fan.pk
    assert comment.author_name == "응원단장"


def test_create_comment_rejects_empty_body(client: Client) -> None:
    """An empty comment body fails validation (422)."""
    post = Post.objects.create(creator=_creator(), body="x")
    resp = _post_json(
        client, f"{POSTS}/{post.id}/comments", {"body": ""}, headers=_bearer(_fan())
    )
    assert resp.status_code == 422


def test_create_comment_requires_auth(client: Client) -> None:
    """An unauthenticated comment is rejected; nothing is created."""
    post = Post.objects.create(creator=_creator(), body="x")
    resp = _post_json(client, f"{POSTS}/{post.id}/comments", {"body": "hi"})
    assert resp.status_code in {401, 403}
    assert Comment.objects.count() == 0


# --- post create (creator owner guard) ---------------------------------------


def test_create_post_forbidden_for_non_creator(client: Client) -> None:
    """A fan who operates no creator profile cannot post (403); nothing created."""
    _creator()  # exists but is not owned by the fan
    resp = _post_json(client, POSTS, {"body": "hi"}, headers=_bearer(_fan()))
    assert resp.status_code == 403
    assert resp.json() == {"detail": "크리에이터만 게시물을 작성할 수 있어요."}
    assert Post.objects.count() == 0


def test_create_post_succeeds_for_owner(client: Client) -> None:
    """A creator owner posts (201); the post is attributed to their creator."""
    fan = _fan()
    creator = Creator.objects.create(handle="mio", name="Mio", owner=fan)
    resp = _post_json(
        client,
        POSTS,
        {"body": "첫 게시물", "media_url": "https://cdn.example/a.png"},
        headers=_bearer(fan),
    )
    assert resp.status_code == 201
    row = resp.json()
    assert row["body"] == "첫 게시물"
    assert row["media_url"] == "https://cdn.example/a.png"
    assert row["creator_handle"] == "mio"
    assert row["like_count"] == 0 and row["comment_count"] == 0
    assert row["liked"] is False
    assert Post.objects.filter(creator=creator).count() == 1


def test_create_post_rejects_non_http_media_url(client: Client) -> None:
    """A non-http(s)/non-relative media_url (e.g. javascript:) is rejected (A5, 422)."""
    fan = _fan()
    Creator.objects.create(handle="mio", name="Mio", owner=fan)
    resp = _post_json(
        client,
        POSTS,
        {"body": "x", "media_url": "javascript:alert(1)"},
        headers=_bearer(fan),
    )
    assert resp.status_code == 422
    assert Post.objects.count() == 0


def test_create_post_accepts_relative_media_url(client: Client) -> None:
    """A site-relative media_url (leading /) is accepted (A5)."""
    fan = _fan()
    Creator.objects.create(handle="mio", name="Mio", owner=fan)
    resp = _post_json(
        client, POSTS, {"body": "x", "media_url": "/uploads/a.png"}, headers=_bearer(fan)
    )
    assert resp.status_code == 201
    assert resp.json()["media_url"] == "/uploads/a.png"


# --- per-user liked flag wiring ----------------------------------------------


def test_liked_flag_is_false_for_anonymous(client: Client) -> None:
    """An anonymous read never breaks and always reports ``liked`` False."""
    post = Post.objects.create(creator=_creator(), body="x")
    Like.objects.create(post=post, user=_fan())  # liked by someone else
    body = client.get(f"{POSTS}/{post.id}").json()
    assert body["liked"] is False
    assert body["like_count"] == 1


def test_liked_flag_is_true_for_the_liking_user(client: Client) -> None:
    """An authenticated read reflects the caller's own like across detail/list/feed."""
    post = Post.objects.create(creator=_creator(), body="x")
    fan = _fan()
    Like.objects.create(post=post, user=fan)
    headers = _bearer(fan)

    detail = client.get(f"{POSTS}/{post.id}", headers=headers).json()
    assert detail["liked"] is True

    listed = client.get(POSTS, headers=headers).json()["items"][0]
    assert listed["liked"] is True

    fed = client.get(FEED, headers=headers).json()["items"][0]
    assert fed["liked"] is True


def test_liked_flag_is_isolated_per_user(client: Client) -> None:
    """One fan's like does not surface as another fan's ``liked``."""
    post = Post.objects.create(creator=_creator(), body="x")
    liker = _fan("liker")
    other = _fan("other")
    Like.objects.create(post=post, user=liker)
    body = client.get(f"{POSTS}/{post.id}", headers=_bearer(other)).json()
    assert body["liked"] is False
    assert body["like_count"] == 1


# --- post edit / delete (creator owner guard, R5-W1A) ------------------------ #


def test_update_post_owner_edits_fields(client: Client) -> None:
    """The owning creator can patch body/media_url/adult; the response reflects it."""
    fan = _fan()
    creator = Creator.objects.create(handle="mio", name="Mio", owner=fan)
    post = Post.objects.create(creator=creator, body="원본", media_url="")
    resp = client.patch(
        f"{POSTS}/{post.id}",
        data=json.dumps({"body": "수정본", "media_url": "/uploads/b.png", "is_adult": True}),
        content_type="application/json",
        headers=_bearer(fan),
    )
    assert resp.status_code == 200
    row = resp.json()
    assert row["body"] == "수정본"
    assert row["media_url"] == "/uploads/b.png"
    assert row["is_adult"] is True
    post.refresh_from_db()
    assert post.body == "수정본" and post.adult_only is True


def test_update_post_returns_fresh_counts(client: Client) -> None:
    """An edit response carries the post's real like/comment counts, not zeros."""
    fan = _fan()
    creator = Creator.objects.create(handle="mio", name="Mio", owner=fan)
    post = Post.objects.create(creator=creator, body="x")
    Like.objects.create(post=post, user=_fan("liker"))
    Comment.objects.create(post=post, author_name="팬", body="좋아요")
    resp = client.patch(
        f"{POSTS}/{post.id}",
        data=json.dumps({"body": "y"}),
        content_type="application/json",
        headers=_bearer(fan),
    )
    assert resp.status_code == 200
    assert resp.json()["like_count"] == 1
    assert resp.json()["comment_count"] == 1


def test_update_post_not_owned_is_404(client: Client) -> None:
    """Patching another creator's post is a 404 (no existence leak); nothing changes."""
    owner = _fan()
    Creator.objects.create(handle="mio", name="Mio", owner=owner)
    stranger_creator = _creator("rabbit")
    post = Post.objects.create(creator=stranger_creator, body="남의 글")
    resp = client.patch(
        f"{POSTS}/{post.id}",
        data=json.dumps({"body": "탈취"}),
        content_type="application/json",
        headers=_bearer(owner),
    )
    assert resp.status_code == 404
    post.refresh_from_db()
    assert post.body == "남의 글"


def test_update_post_by_non_creator_is_404(client: Client) -> None:
    """A caller who operates no creator owns no post, so a patch 404s."""
    post = Post.objects.create(creator=_creator(), body="x")
    resp = client.patch(
        f"{POSTS}/{post.id}",
        data=json.dumps({"body": "y"}),
        content_type="application/json",
        headers=_bearer(_fan()),
    )
    assert resp.status_code == 404


def test_update_post_rejects_bad_media_url(client: Client) -> None:
    """A non-http(s)/non-relative media_url is rejected on edit too (A5, 422)."""
    fan = _fan()
    creator = Creator.objects.create(handle="mio", name="Mio", owner=fan)
    post = Post.objects.create(creator=creator, body="x")
    resp = client.patch(
        f"{POSTS}/{post.id}",
        data=json.dumps({"media_url": "javascript:alert(1)"}),
        content_type="application/json",
        headers=_bearer(fan),
    )
    assert resp.status_code == 422


def test_delete_post_owner_hard_deletes_with_cascade(client: Client) -> None:
    """The owner hard-deletes their post; its comments and likes CASCADE away."""
    fan = _fan()
    creator = Creator.objects.create(handle="mio", name="Mio", owner=fan)
    post = Post.objects.create(creator=creator, body="지울 글")
    Like.objects.create(post=post, user=_fan("liker"))
    Comment.objects.create(post=post, author_name="팬", body="댓글")
    resp = client.delete(f"{POSTS}/{post.id}", headers=_bearer(fan))
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    assert not Post.objects.filter(id=post.id).exists()
    assert Like.objects.filter(post_id=post.id).count() == 0
    assert Comment.objects.filter(post_id=post.id).count() == 0


def test_delete_post_not_owned_is_404(client: Client) -> None:
    """Deleting another creator's post is a 404; the post survives."""
    owner = _fan()
    Creator.objects.create(handle="mio", name="Mio", owner=owner)
    post = Post.objects.create(creator=_creator("rabbit"), body="남의 글")
    resp = client.delete(f"{POSTS}/{post.id}", headers=_bearer(owner))
    assert resp.status_code == 404
    assert Post.objects.filter(id=post.id).exists()


def test_comment_notifies_post_creator_owner(client: Client) -> None:
    """Commenting on a post appends a comment notification to the creator owner."""
    from apps.content.models import Post
    from apps.notification.models import Notification

    owner = _fan("작가")
    creator = Creator.objects.create(handle="hooked", name="훅크리", owner=owner)
    post = Post.objects.create(creator=creator, body="본문")
    fan = _fan("댓글팬")
    resp = _post_json(
        client,
        f"/api/posts/{post.id}/comments",
        {"body": "응원합니다"},
        headers=_bearer(fan),
    )
    assert resp.status_code == 201
    row = Notification.objects.filter(recipient=owner, kind="comment").first()
    assert row is not None
    assert row.href == f"/post/{post.id}"

    # 오너 자신의 셀프 댓글은 알림을 만들지 않는다.
    _post_json(
        client,
        f"/api/posts/{post.id}/comments",
        {"body": "셀프"},
        headers=_bearer(owner),
    )
    assert Notification.objects.filter(recipient=owner, kind="comment").count() == 1
