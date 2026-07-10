"""Follow / unfollow write API for creators (SDLC 09 §4, E11/B4).

The read side (follower counts, the ``following`` flag) lives in the creator app;
this module owns only the *mutations*. Both are idempotent — following an already
followed creator (or unfollowing one you don't follow) is a no-op that still
returns the current truth ``{following, followers}`` so the client can reconcile
its optimistic state against the server count.

Mounted on the ``/creators`` prefix so the wire contract is
``PUT|DELETE /api/creators/{handle}/follow`` — a natural extension of the creator
profile the creator app already serves under that prefix.

Writes are gated by :data:`~apps.identity.auth.fan_auth` (bearer or the web
access cookie) and rate-limited per user (:func:`config.throttle.user_write_throttle`).
"""

from __future__ import annotations

import uuid

from django.db import IntegrityError, transaction
from django.http import HttpRequest
from ninja import Router, Schema

from apps.creator.models import Creator
from apps.identity.auth import authed, fan_auth
from apps.notification.services import notify
from apps.social.models import CreatorBlock, Follow
from config.api import api
from config.errors import ErrorCode
from config.throttle import user_write_throttle

router = Router(tags=["social"])


class ErrorOut(Schema):
    """Stable error shape for social endpoints."""

    detail: str


class FollowOut(Schema):
    """Follow-edge state after a mutation (fresh aggregate follower count)."""

    following: bool
    followers: int


def _followers(creator: Creator) -> int:
    """Current follower count for a creator (authoritative post-mutation value)."""
    return Follow.objects.filter(creator=creator).count()


@router.put(
    "/{handle}/follow",
    response={200: FollowOut, 404: ErrorOut},
    auth=fan_auth,
    throttle=user_write_throttle("60/min"),
)
def follow_creator(
    request: HttpRequest, handle: str
) -> tuple[int, FollowOut | ErrorOut]:
    """Follow a creator; idempotent (a second follow is a no-op, still 200)."""
    account = authed(request)
    creator = Creator.objects.filter(handle=handle).first()
    if creator is None:
        return 404, ErrorOut(detail="creator not found")
    created = False
    try:
        # Idempotent under concurrency: the unique (follower, creator) constraint
        # collapses a double-follow race into a single edge rather than an error.
        with transaction.atomic():
            _, created = Follow.objects.get_or_create(follower=account, creator=creator)
    except IntegrityError:
        pass
    # 알림은 실제 신규 팔로우에만 — 멱등 재팔로우/자기 크리에이터 팔로우는 제외.
    if created and creator.owner is not None and creator.owner != account:
        notify(
            creator.owner,
            "follow",
            f"{account.nickname}님이 회원님을 팔로우했습니다",
            href=f"/creator/{creator.handle}",
        )
    return 200, FollowOut(following=True, followers=_followers(creator))


@router.delete(
    "/{handle}/follow",
    response={200: FollowOut, 404: ErrorOut},
    auth=fan_auth,
    throttle=user_write_throttle("60/min"),
)
def unfollow_creator(
    request: HttpRequest, handle: str
) -> tuple[int, FollowOut | ErrorOut]:
    """Unfollow a creator; idempotent (unfollowing a non-follow is a no-op)."""
    account = authed(request)
    creator = Creator.objects.filter(handle=handle).first()
    if creator is None:
        return 404, ErrorOut(detail="creator not found")
    Follow.objects.filter(follower=account, creator=creator).delete()
    return 200, FollowOut(following=False, followers=_followers(creator))


api.add_router("/creators", router)


# --------------------------------------------------------------------------- #
# Personal creator block (ASS-226). A fan hides a creator from their OWN
# aggregate surfaces (feed/discovery/search). This is NOT operator moderation
# (apps.safety.UserBlock) — it is fan-controlled, carries no reason code, and is a
# plain create/delete edge. The read-side gating lives at each aggregate call site
# via ``apps.social.models.blocked_creator_ids``; this router owns the mutations +
# the settings-screen list.
# --------------------------------------------------------------------------- #
blocks_router = Router(auth=fan_auth, tags=["social-blocks"])


class BlockError(Schema):
    """Coded error shape for block endpoints (``detail`` copy + stable ``code``)."""

    detail: str
    code: str


class BlockIn(Schema):
    """Request body to block a creator (by id)."""

    creator_id: uuid.UUID


class BlockOut(Schema):
    """Block-edge state after a mutation (lets the client reconcile its state)."""

    blocked: bool
    creator_id: uuid.UUID


class BlockedCreatorOut(Schema):
    """One blocked creator, for the fan's block-list settings screen."""

    creator_id: uuid.UUID
    name: str
    handle: str


@blocks_router.post(
    "",
    response={200: BlockOut, 404: BlockError},
    throttle=user_write_throttle("30/min"),
)
def block_creator(request: HttpRequest, payload: BlockIn) -> tuple[int, BlockOut | BlockError]:
    """Block a creator; idempotent (a second block is a no-op, still 200).

    Blocking auto-unfollows (standard mute/block UX): a fan who blocks a creator
    they follow should not keep receiving that creator's follow-derived surfaces.
    An unknown creator id is 404 (``BlockTargetNotFound``) — unlike the 19+ gate,
    a personal block does not hide the target's existence.
    """
    account = authed(request)
    creator = Creator.objects.filter(id=payload.creator_id).first()
    if creator is None:
        return 404, BlockError(
            detail="크리에이터를 찾을 수 없어요.",
            code=ErrorCode.BLOCK_TARGET_NOT_FOUND.value,
        )
    try:
        # Idempotent under concurrency: the unique (blocker, creator) constraint
        # collapses a double-block race into a single edge rather than an error.
        with transaction.atomic():
            CreatorBlock.objects.get_or_create(blocker=account, creator=creator)
    except IntegrityError:
        pass
    # 차단 시 팔로우 중이면 자동 언팔로우 (표준 UX). 미팔로우면 무해한 no-op.
    Follow.objects.filter(follower=account, creator=creator).delete()
    return 200, BlockOut(blocked=True, creator_id=creator.id)


@blocks_router.delete(
    "/{creator_id}",
    response={200: BlockOut},
    throttle=user_write_throttle("30/min"),
)
def unblock_creator(request: HttpRequest, creator_id: uuid.UUID) -> tuple[int, BlockOut]:
    """Unblock a creator; idempotent (unblocking a non-block is a no-op, still 200)."""
    account = authed(request)
    CreatorBlock.objects.filter(blocker=account, creator_id=creator_id).delete()
    return 200, BlockOut(blocked=False, creator_id=creator_id)


@blocks_router.get("", response=list[BlockedCreatorOut])
def list_blocks(request: HttpRequest) -> list[BlockedCreatorOut]:
    """List the creators the requesting fan has blocked (settings screen)."""
    account = authed(request)
    blocks = (
        CreatorBlock.objects.filter(blocker=account)
        .select_related("creator")
        .order_by("-created_at")
    )
    return [
        BlockedCreatorOut(
            creator_id=block.creator_id,
            name=block.creator.name,
            handle=block.creator.handle,
        )
        for block in blocks
    ]


api.add_router("/fan/blocks", blocks_router)
