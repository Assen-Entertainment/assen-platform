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

from typing import cast

from django.db import IntegrityError, transaction
from django.http import HttpRequest
from ninja import Router, Schema

from apps.creator.models import Creator
from apps.identity.auth import fan_auth
from apps.identity.models import Account
from apps.notification.services import notify
from apps.social.models import Follow
from config.api import api
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
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
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
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    creator = Creator.objects.filter(handle=handle).first()
    if creator is None:
        return 404, ErrorOut(detail="creator not found")
    Follow.objects.filter(follower=account, creator=creator).delete()
    return 200, FollowOut(following=False, followers=_followers(creator))


api.add_router("/creators", router)
