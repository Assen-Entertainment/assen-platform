"""Social graph model — Follow (SDLC 09 §3 — social context, E11/B1).

``Follow`` powers follower counts and the ``following`` flag on creator
profiles. The follow *mutations* land in B4 — B1/B2 only need the model and the
read-side derivation. Blocking/moderation is NOT modelled here: it reuses the
existing ``apps.safety.UserBlock`` (SDLC 09 §8 — safety→moderation is reused),
which already supports account-level blocks with scopes.

Migration-less app (``migrate --run-syncdb``); do not add a migrations package.
"""

from __future__ import annotations

import uuid

from django.db import models


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
