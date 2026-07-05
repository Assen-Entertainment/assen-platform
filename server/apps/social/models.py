"""Social graph models — Follow + CreatorBlock (SDLC 09 §3 — social context).

``Follow`` powers follower counts and the ``following`` flag on creator profiles.

``CreatorBlock`` is a fan's *personal* block of a creator: it hides that creator
from the blocking fan's own aggregate surfaces (feed, discovery, search). It is a
DIFFERENT concept from ``apps.safety.UserBlock`` — that one is *operator*
moderation (a closed reason enum, the ``user_blocked`` event, scope-based denial,
lifted-not-deleted). A personal block carries no moderation semantics, is fully
fan-controlled, affects only what THAT fan sees, and is a plain create/delete
edge. The two must never be conflated.

Migration-less app (``migrate --run-syncdb``); do not add a migrations package.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from apps.identity.models import Account


class Follow(models.Model):
    """A fan following a creator. Uniqueness prevents double-follow."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follower = models.ForeignKey(
        "identity.Account",
        on_delete=models.CASCADE,
        related_name="following_set",
    )
    creator = models.ForeignKey(
        "creator.Creator",
        on_delete=models.CASCADE,
        related_name="followers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "creator"], name="uniq_follow_follower_creator"
            ),
        ]
        indexes = [
            models.Index(fields=["creator", "-created_at"]),
            models.Index(fields=["follower", "-created_at"]),
        ]

    def __str__(self) -> str:
        """Identify the follow edge."""
        return f"follow:{self.follower_id}->{self.creator_id}"


class CreatorBlock(models.Model):
    """A fan's *personal* block of a creator (hides them from the fan's surfaces).

    When ``blocker`` blocks ``creator``, that creator's content is excluded from
    the blocker's aggregate surfaces (feed, discovery, search) — see
    :func:`blocked_creator_ids`. This is NOT operator moderation: it is unrelated
    to :class:`apps.safety.UserBlock` (which owns the ``user_blocked`` event, the
    closed block-reason enum, and scope-based denial). A personal block is a plain
    create/delete edge with no reason code and no audit-retention rule, and it only
    changes what the blocking fan sees.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blocker = models.ForeignKey(
        "identity.Account",
        on_delete=models.CASCADE,
        related_name="creator_blocks",
    )
    creator = models.ForeignKey(
        "creator.Creator",
        on_delete=models.CASCADE,
        related_name="blocked_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "creator"],
                name="uniq_creatorblock_blocker_creator",
            ),
        ]
        indexes = [
            models.Index(fields=["blocker", "-created_at"]),
        ]

    def __str__(self) -> str:
        """Identify the personal-block edge."""
        return f"creatorblock:{self.blocker_id}->{self.creator_id}"


def blocked_creator_ids(account: Account | None) -> set[uuid.UUID]:
    """Creator ids the fan has personally blocked (empty set for anonymous).

    One query, materialised as a set so a caller can
    ``.exclude(creator_id__in=blocked_creator_ids(account))`` on any listing without
    an N+1. Anonymous callers (``account is None``) get an empty set and short-circuit
    without a query: a personal block only affects the fan who set it, never an
    anonymous or logged-out read.
    """
    if account is None:
        return set()
    return set(
        CreatorBlock.objects.filter(blocker=account).values_list("creator_id", flat=True)
    )
