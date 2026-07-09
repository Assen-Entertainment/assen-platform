"""Read + write API for posts, feed, and comments (SDLC 09 §4, E11/B2+B4).

Reads are anonymous but personalised when a token is presented: ``liked`` is
derived per user via :func:`~apps.identity.auth.resolve_optional_account` (a
single ``Exists`` subquery, so no N+1 and no broken anonymous read). Like/comment
counts are annotated (single query, no drift). Creator-scoped posts use
``?creator_id=`` rather than a nested path so the ``/creators`` prefix stays owned
by the creator app.

Writes (like toggle, comment create, post create — E11/B4) are gated by
:data:`~apps.identity.auth.fan_auth` and rate-limited per user. Posting requires
the caller to operate a creator profile (owner guard); everyone can like/comment.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, OuterRef, QuerySet
from django.http import HttpRequest
from ninja import Router, Schema
from pydantic import Field, field_validator

from apps.content.models import Comment, Like, Post
from apps.creator.models import Creator
from apps.identity.auth import authed, fan_auth, resolve_optional_account
from apps.identity.models import Account
from apps.notification.services import notify
from apps.social.models import blocked_creator_ids
from config.api import api
from config.errors import ErrorCode
from config.pagination import paginate
from config.throttle import user_write_throttle

posts_router = Router(tags=["content"])
feed_router = Router(tags=["content"])
# Owner post management (studio surface — consumer 19+ gate NOT applied; the owner
# always sees their own adult/full posts). Mirrors commerce ``/studio/products``.
studio_posts_router = Router(auth=fan_auth, tags=["studio-content"])


class ErrorOut(Schema):
    """Stable error shape for content endpoints."""

    detail: str


class InteractionBlockedError(Schema):
    """422 body when a fan interacts with a personally-blocked creator's content.

    Carries the stable :class:`~config.errors.ErrorCode` value the web branches on
    (``InteractionBlocked``) alongside the human ``detail`` copy, mirroring the
    ``{detail, code}`` shape used by commerce/membership.
    """

    detail: str
    code: str


# 422 copy shared by every blocked write interaction (like/comment/order).
_INTERACTION_BLOCKED_DETAIL = "차단한 크리에이터의 콘텐츠에는 상호작용할 수 없어요."


def _validated_media_url(value: str) -> str:
    """Reject non-http(s) / non-relative media URLs (A5).

    A post's ``media_url`` is echoed straight into the feed, so an attacker-supplied
    ``javascript:``/``data:`` scheme could drive XSS on a naive renderer. Accept only
    an absolute http(s) URL or a site-relative path (leading ``/``); anything else
    fails schema validation (422). Empty stays allowed (no media).
    """
    if value == "" or value.startswith(("/", "http://", "https://")):
        return value
    raise ValueError("media_url must be an http(s) URL or a site-relative path.")


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
    is_adult: bool = False
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


class LikeOut(Schema):
    """Like state after a toggle (fresh aggregate like count)."""

    liked: bool
    like_count: int


class CommentIn(Schema):
    """Request body for creating a comment."""

    body: str = Field(min_length=1, max_length=1000)


class PostIn(Schema):
    """Request body for creating a post (author is the caller's creator profile)."""

    body: str = Field(max_length=2000)
    media_url: str = Field(default="", max_length=500)
    # 19+ 성인 등급 토글 → Post.adult_only. 노출은 서버 게이트(ENABLE_ADULT_CONTENT +
    # adult_verified 뷰어)가 최종 결정 — 작성은 라이브에서도 허용하되 기본 노출은 숨김.
    is_adult: bool = False

    @field_validator("media_url")
    @classmethod
    def _validate_media_url(cls, value: str) -> str:
        """Reject non-http(s) / non-relative media URLs (A5)."""
        return _validated_media_url(value)


class PostPatch(Schema):
    """Request body to update a post; only the provided fields are applied."""

    body: str | None = Field(default=None, max_length=2000)
    media_url: str | None = Field(default=None, max_length=500)
    is_adult: bool | None = None

    @field_validator("media_url")
    @classmethod
    def _validate_media_url(cls, value: str | None) -> str | None:
        """Validate media_url only when provided (A5, mirrors ``PostIn``)."""
        return None if value is None else _validated_media_url(value)


class PostAck(Schema):
    """Bare status ack for a post mutation that returns no body (delete)."""

    status: str


def _adult_allowed(viewer: Account | None) -> bool:
    """Whether 19+ (``adult_only``) items may be shown to ``viewer``.

    Fail-closed: ``ENABLE_ADULT_CONTENT`` is False by default, so every adult item
    is hidden from EVERYONE — the age-gate has no live content to leak before the
    법무 사인 (R3 정본 §55). When the flag is on (dev/test) an item is shown only to
    an ``adult_verified`` viewer; an anonymous or unverified viewer still gets none.
    """
    return bool(
        settings.ENABLE_ADULT_CONTENT and viewer is not None and viewer.adult_verified
    )


def _post_qs(account: Account | None = None) -> QuerySet[Post]:
    """Posts with annotated like/comment counts and their creator preloaded.

    When ``account`` is given, a per-user ``is_liked`` flag is annotated via a
    single ``Exists`` subquery — no extra per-row query — so a list stays one
    query. Anonymous callers pass ``None`` and get no annotation (``liked`` False).

    19+ gating is applied here (the single funnel for every public post read —
    list/feed/single): ``adult_only`` posts are excluded unless
    :func:`_adult_allowed`, so a direct single fetch of an adult post by a
    non-permitted viewer 404s (no existence leak) rather than slipping past the list
    filter.
    """
    queryset = Post.objects.select_related("creator").annotate(
        like_count=Count("likes", distinct=True),
        comment_count=Count("comments", distinct=True),
    )
    if account is not None:
        queryset = queryset.annotate(
            is_liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=account))
        )
    if not _adult_allowed(account):
        queryset = queryset.exclude(adult_only=True)
    return queryset


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
        liked=bool(getattr(post, "is_liked", False)),
        is_adult=post.adult_only,
        created_at=post.created_at,
    )


def _comment_out(comment: Comment) -> CommentOut:
    """Build the comment response using a *display* name only.

    Never expose ``Account.fan_id`` (the internal cross-system identifier): fall
    back to the account's display ``nickname`` and finally a static label, so a
    public endpoint can never be used to harvest fan ids.
    """
    author = comment.author_name
    if not author and comment.author is not None:
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
    """List posts, newest first; filter to one creator via ``?creator_id=``.

    Personal-block gating: the global (unfiltered) list is an aggregate surface, so
    personally blocked creators are excluded. A ``?creator_id=`` request is explicit
    creator-scoped navigation (a profile visit), so it is returned even for a blocked
    creator — the web renders the block state; a personal block is not existence hiding.
    """
    account = resolve_optional_account(request)
    queryset = _post_qs(account).order_by("-created_at", "id")
    if creator_id is not None:
        queryset = queryset.filter(creator_id=creator_id)
    else:
        queryset = queryset.exclude(creator_id__in=blocked_creator_ids(account))
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return PostPage(items=[_post_out(p) for p in items], next_cursor=next_cursor)


@posts_router.get("/{post_id}", response={200: PostOut, 404: ErrorOut})
def get_post(
    request: HttpRequest, post_id: uuid.UUID
) -> tuple[int, PostOut | ErrorOut]:
    """Fetch a single post; 404 if unknown."""
    post = _post_qs(resolve_optional_account(request)).filter(id=post_id).first()
    if post is None:
        return 404, ErrorOut(detail="post not found")
    return 200, _post_out(post)


@posts_router.post(
    "",
    response={201: PostOut, 403: ErrorOut},
    auth=fan_auth,
    throttle=user_write_throttle("6/min"),
)
def create_post(request: HttpRequest, data: PostIn) -> tuple[int, PostOut | ErrorOut]:
    """Create a post as the caller's creator profile; 403 if they operate none.

    Owner guard: only an account that operates a :class:`Creator` may post, and
    the post is always attributed to *that* creator — the author is never taken
    from client input, so a fan cannot post as someone else.
    """
    account = authed(request)
    creator = Creator.objects.filter(owner=account).first()
    if creator is None:
        return 403, ErrorOut(detail="크리에이터만 게시물을 작성할 수 있어요.")
    post = Post.objects.create(
        creator=creator,
        body=data.body,
        media_url=data.media_url,
        adult_only=data.is_adult,
    )
    # A fresh post carries no count annotations; _post_out defaults them to 0 and
    # liked to False, which is correct for a just-created post. ``post.creator`` is
    # already the in-memory creator (passed to create), so no extra query.
    return 201, _post_out(post)


def _owned_post(account: Account, post_id: uuid.UUID) -> Post | None:
    """The post ``post_id`` iff it belongs to the creator ``account`` operates.

    Owner guard for post management (mirrors ``create_post``): the scope is always
    the caller's own creator, so a post that is unknown or owned by someone else is
    indistinguishable (``None`` → 404, no existence leak). An account that operates
    no creator owns no posts, so it always gets ``None``.
    """
    creator = Creator.objects.filter(owner=account).first()
    if creator is None:
        return None
    return Post.objects.filter(id=post_id, creator=creator).first()


def _annotated_post(post_id: uuid.UUID, account: Account) -> Post:
    """Reload a post with like/comment counts and the caller's ``is_liked`` flag.

    Used after an owner edit to return fresh aggregates. Bypasses the 19+ read gate
    (the owner manages their own post, including one they just marked adult) but
    stays scoped to a known-owned id, so nothing is leaked.
    """
    return (
        Post.objects.select_related("creator")
        .annotate(
            like_count=Count("likes", distinct=True),
            comment_count=Count("comments", distinct=True),
            is_liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=account)),
        )
        .get(id=post_id)
    )


@studio_posts_router.get("", response={200: PostPage, 403: ErrorOut})
def studio_list_posts(
    request: HttpRequest, cursor: str | None = None, limit: int | None = None
) -> tuple[int, PostPage | ErrorOut]:
    """List the caller's own creator's posts — including 19+ — newest first.

    Owner surface (mirrors ``commerce.studio_list_products``): the consumer 19+ gate
    (:func:`_post_qs`) is deliberately NOT applied, so the owner always sees their own
    adult/full posts regardless of ``ENABLE_ADULT_CONTENT``. 403 if the caller
    operates no creator. Each row carries the same annotations as :func:`_annotated_post`
    (like/comment counts + the owner's own ``liked`` flag), cursor-paginated.
    """
    account = authed(request)
    creator = Creator.objects.filter(owner=account).first()
    if creator is None:
        return 403, ErrorOut(detail="크리에이터만 게시물을 관리할 수 있어요.")
    queryset = (
        Post.objects.filter(creator=creator)
        .select_related("creator")
        .annotate(
            like_count=Count("likes", distinct=True),
            comment_count=Count("comments", distinct=True),
            is_liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=account)),
        )
        .order_by("-created_at", "id")
    )
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return 200, PostPage(items=[_post_out(p) for p in items], next_cursor=next_cursor)


@posts_router.patch(
    "/{post_id}",
    response={200: PostOut, 404: ErrorOut},
    auth=fan_auth,
    throttle=user_write_throttle("6/min"),
)
def update_post(
    request: HttpRequest, post_id: uuid.UUID, data: PostPatch
) -> tuple[int, PostOut | ErrorOut]:
    """Update fields on the caller's own post; 404 if unknown or not theirs (no leak).

    Owner guard identical to ``create_post`` (scope is the caller's creator). Only
    the provided fields (``body``/``media_url``/``is_adult``) are applied; the
    ``media_url`` scheme is re-validated (A5). The response reflects fresh
    like/comment counts and the caller's ``liked`` flag.
    """
    account = authed(request)
    post = _owned_post(account, post_id)
    if post is None:
        return 404, ErrorOut(detail="post not found")
    if data.body is not None:
        post.body = data.body
    if data.media_url is not None:
        post.media_url = data.media_url
    if data.is_adult is not None:
        post.adult_only = data.is_adult
    post.save()
    return 200, _post_out(_annotated_post(post.id, account))


@posts_router.delete(
    "/{post_id}",
    response={200: PostAck, 404: ErrorOut},
    auth=fan_auth,
    throttle=user_write_throttle("6/min"),
)
def delete_post(
    request: HttpRequest, post_id: uuid.UUID
) -> tuple[int, PostAck | ErrorOut]:
    """Hard-delete the caller's own post; 404 if unknown or not theirs (no leak).

    Owner guard identical to ``create_post``. Unlike an order/tier, a post has no
    history constraint, so deletion is a hard delete — its comments and likes
    CASCADE (``Comment.post`` / ``Like.post`` are ``on_delete=CASCADE``).
    """
    account = authed(request)
    post = _owned_post(account, post_id)
    if post is None:
        return 404, ErrorOut(detail="post not found")
    post.delete()
    return 200, PostAck(status="deleted")


@posts_router.put(
    "/{post_id}/like",
    response={200: LikeOut, 404: ErrorOut, 422: InteractionBlockedError},
    auth=fan_auth,
    throttle=user_write_throttle("60/min"),
)
def like_post(
    request: HttpRequest, post_id: uuid.UUID
) -> tuple[int, LikeOut | ErrorOut | InteractionBlockedError]:
    """Like a post; idempotent (a second like is a no-op, still 200)."""
    account = authed(request)
    # 19+ gate (same funnel as reads): an adult post the caller may not see 404s here
    # too, so the like endpoint can't be used to touch or probe a gated post.
    post = _post_qs(account).filter(id=post_id).first()
    if post is None:
        return 404, ErrorOut(detail="post not found")
    # Personal-block consistency (F4): the read stays allowed, but a new write
    # interaction against a creator this fan has blocked is refused. One set query.
    if post.creator_id in blocked_creator_ids(account):
        return 422, InteractionBlockedError(
            detail=_INTERACTION_BLOCKED_DETAIL, code=ErrorCode.INTERACTION_BLOCKED.value
        )
    # No notification is emitted on a like (B6): likes are high-volume and would
    # spam the creator's feed. Only comments notify. The web mock's like-notification
    # is demo-only and intentionally not mirrored server-side.
    try:
        # Idempotent under concurrency: the unique (post, user) constraint
        # collapses a double-like race into a single edge rather than an error.
        with transaction.atomic():
            Like.objects.get_or_create(post=post, user=account)
    except IntegrityError:
        pass
    return 200, LikeOut(liked=True, like_count=Like.objects.filter(post=post).count())


@posts_router.delete(
    "/{post_id}/like",
    response={200: LikeOut, 404: ErrorOut},
    auth=fan_auth,
    throttle=user_write_throttle("60/min"),
)
def unlike_post(
    request: HttpRequest, post_id: uuid.UUID
) -> tuple[int, LikeOut | ErrorOut]:
    """Unlike a post; idempotent (unliking a non-liked post is a no-op).

    Retraction is exempt from the personal-block gate (F4): unliking is not a *new*
    interaction against the creator but cleanup of the fan's own existing like, so a
    fan who blocked the creator after liking can still withdraw that like (standard
    block UX — you can always remove your own trace). New interactions
    (``like``/comment/order) stay refused while blocked; only the 19+ read funnel
    still applies here, so a gated adult post 404s.
    """
    account = authed(request)
    # 19+ gate (same funnel as reads): a gated adult post 404s here too.
    post = _post_qs(account).filter(id=post_id).first()
    if post is None:
        return 404, ErrorOut(detail="post not found")
    Like.objects.filter(post=post, user=account).delete()
    return 200, LikeOut(liked=False, like_count=Like.objects.filter(post=post).count())


@posts_router.get("/{post_id}/comments", response={200: CommentPage, 404: ErrorOut})
def list_comments(
    request: HttpRequest,
    post_id: uuid.UUID,
    cursor: str | None = None,
    limit: int | None = None,
) -> tuple[int, CommentPage | ErrorOut]:
    """List a post's comments, oldest first; 404 if the post is unknown or gated."""
    # Anonymous-readable, but 19+ gated through the same funnel as the post reads: a
    # gated adult post 404s (no existence leak) so its comment thread can't be read
    # past the gate by an anonymous or unverified viewer.
    if not _post_qs(resolve_optional_account(request)).filter(id=post_id).exists():
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


@posts_router.post(
    "/{post_id}/comments",
    response={201: CommentOut, 404: ErrorOut, 422: InteractionBlockedError},
    auth=fan_auth,
    throttle=user_write_throttle("10/min"),
)
def create_comment(
    request: HttpRequest, post_id: uuid.UUID, data: CommentIn
) -> tuple[int, CommentOut | ErrorOut | InteractionBlockedError]:
    """Add a comment to a post as the authenticated fan; 404 if the post is unknown.

    ``author`` is the account; ``author_name`` denormalises the display nickname so
    the comment renders identically to a seeded one (and _comment_out never leaks
    the internal fan_id).
    """
    account = authed(request)
    # 19+ gate (same funnel as reads): a gated adult post 404s so a non-permitted
    # viewer can neither read nor comment on it.
    post = _post_qs(account).select_related("creator__owner").filter(id=post_id).first()
    if post is None:
        return 404, ErrorOut(detail="post not found")
    # Personal-block consistency (F4): reads stay allowed, but a new comment on a
    # blocked creator's post is refused. One set query.
    if post.creator_id in blocked_creator_ids(account):
        return 422, InteractionBlockedError(
            detail=_INTERACTION_BLOCKED_DETAIL, code=ErrorCode.INTERACTION_BLOCKED.value
        )
    comment = Comment.objects.create(
        post=post, author=account, author_name=account.nickname, body=data.body
    )
    # 알림 훅 — 포스트의 크리에이터 오너에게(자기 포스트 셀프 댓글은 제외).
    owner = post.creator.owner
    if owner is not None and owner != account:
        notify(
            owner,
            "comment",
            f"{account.nickname}님이 댓글을 남겼습니다",
            href=f"/post/{post.id}",
        )
    return 201, _comment_out(comment)


@feed_router.get("", response=PostPage)
def feed(
    request: HttpRequest, cursor: str | None = None, limit: int | None = None
) -> PostPage:
    """Anonymous feed = most recent posts across creators.

    Personalised (following-only) feed needs a richer ranking and lands later; for
    now this returns the same recent-posts page as ``/posts``, but with the
    per-user ``liked`` flag filled in when the caller is authenticated.

    The feed is an aggregate surface, so posts from creators the caller has
    personally blocked are excluded (anonymous callers block nothing).
    """
    account = resolve_optional_account(request)
    queryset = (
        _post_qs(account)
        .exclude(creator_id__in=blocked_creator_ids(account))
        .order_by("-created_at", "id")
    )
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return PostPage(items=[_post_out(p) for p in items], next_cursor=next_cursor)


api.add_router("/posts", posts_router)
api.add_router("/feed", feed_router)
api.add_router("/studio/posts", studio_posts_router)
