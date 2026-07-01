"""Public read API for posts, feed, and comments (SDLC 09 §4, E11/B2).

Anonymous reads. Like/comment counts are annotated (single query, no drift).
``liked`` is always ``False`` here — it becomes per-user once auth lands (B3).
Creator-scoped posts use ``?creator_id=`` rather than a nested path so the
``/creators`` prefix stays owned by the creator app.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from django.db.models import Count, QuerySet
from django.http import HttpRequest
from ninja import Router, Schema

from apps.content.models import Comment, Post
from config.api import api
from config.pagination import paginate

posts_router = Router(tags=["content"])
feed_router = Router(tags=["content"])


class ErrorOut(Schema):
    """Stable error shape for content endpoints."""

    detail: str


class PostOut(Schema):
    """Feed post (maps to the frontend ``Post`` type)."""

    id: uuid.UUID
    creator_id: uuid.UUID
    creator_name: str
    creator_handle: str
    verified: bool
    body: str
    media_url: str
    like_count: int
    comment_count: int
    liked: bool = False
    created_at: datetime


class PostPage(Schema):
    """One page of posts plus the next cursor."""

    items: list[PostOut]
    next_cursor: str | None = None


class CommentOut(Schema):
    """A comment (maps to the frontend ``Comment`` type; ``author`` is a display name)."""

    id: uuid.UUID
    post_id: uuid.UUID
    author: str
    body: str
    created_at: datetime


class CommentPage(Schema):
    """One page of comments plus the next cursor."""

    items: list[CommentOut]
    next_cursor: str | None = None


def _post_qs() -> QuerySet[Post]:
    """Posts with annotated like/comment counts and their creator preloaded."""
    return Post.objects.select_related("creator").annotate(
        like_count=Count("likes", distinct=True),
        comment_count=Count("comments", distinct=True),
    )


def _post_out(post: Post) -> PostOut:
    """Build the post response from an annotated row."""
    return PostOut(
        id=post.id,
        creator_id=post.creator_id,
        creator_name=post.creator.name,
        creator_handle=post.creator.handle,
        verified=post.creator.verified,
        body=post.body,
        media_url=post.media_url,
        like_count=getattr(post, "like_count", 0),
        comment_count=getattr(post, "comment_count", 0),
        liked=False,
        created_at=post.created_at,
    )


def _comment_out(comment: Comment) -> CommentOut:
    """Build the comment response using a *display* name only.

    Never expose ``Account.fan_id`` (the internal cross-system identifier): fall
    back to the account's display ``nickname`` and finally a static label, so a
    public endpoint can never be used to harvest fan ids.
    """
    author = comment.author_name
    if not author and comment.author_id:
        author = comment.author.nickname
    return CommentOut(
        id=comment.id,
        post_id=comment.post_id,
        author=author or "익명",
        body=comment.body,
        created_at=comment.created_at,
    )


@posts_router.get("", response=PostPage)
def list_posts(
    request: HttpRequest,
    creator_id: uuid.UUID | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> PostPage:
    """List posts, newest first; filter to one creator via ``?creator_id=``."""
    del request
    queryset = _post_qs().order_by("-created_at", "id")
    if creator_id is not None:
        queryset = queryset.filter(creator_id=creator_id)
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return PostPage(items=[_post_out(p) for p in items], next_cursor=next_cursor)


@posts_router.get("/{post_id}", response={200: PostOut, 404: ErrorOut})
def get_post(
    request: HttpRequest, post_id: uuid.UUID
) -> tuple[int, PostOut | ErrorOut]:
    """Fetch a single post; 404 if unknown."""
    del request
    post = _post_qs().filter(id=post_id).first()
    if post is None:
        return 404, ErrorOut(detail="post not found")
    return 200, _post_out(post)


@posts_router.get("/{post_id}/comments", response={200: CommentPage, 404: ErrorOut})
def list_comments(
    request: HttpRequest,
    post_id: uuid.UUID,
    cursor: str | None = None,
    limit: int | None = None,
) -> tuple[int, CommentPage | ErrorOut]:
    """List a post's comments, oldest first; 404 if the post is unknown."""
    del request
    if not Post.objects.filter(id=post_id).exists():
        return 404, ErrorOut(detail="post not found")
    queryset = (
        Comment.objects.filter(post_id=post_id)
        .select_related("author")
        .order_by("created_at", "id")
    )
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return 200, CommentPage(
        items=[_comment_out(c) for c in items], next_cursor=next_cursor
    )


@feed_router.get("", response=PostPage)
def feed(
    request: HttpRequest, cursor: str | None = None, limit: int | None = None
) -> PostPage:
    """Anonymous feed = most recent posts across creators.

    Personalised (following-only) feed needs the authenticated user and lands in
    B3/B4; for now this returns the same recent-posts page as ``/posts``.
    """
    del request
    queryset = _post_qs().order_by("-created_at", "id")
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return PostPage(items=[_post_out(p) for p in items], next_cursor=next_cursor)


api.add_router("/posts", posts_router)
api.add_router("/feed", feed_router)
