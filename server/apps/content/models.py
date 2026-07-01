"""Content models — Post, Comment, Like (SDLC 09 §3 — content context, E11/B1).

Posts belong to a creator; likes and comments attach to a post. Like/comment
*counts* are derived (annotated) rather than stored so they cannot drift. The
write mutations (like toggle, comment create) land in B4; B1/B2 provide the
models and the read side.

Comments denormalise ``author_name`` (display string, matching the frontend
``Comment.author``) so seed/anonymous comments render without an account, while
still keeping a nullable ``author`` FK for real authored comments.

Migration-less app (``migrate --run-syncdb``); do not add a migrations package.
"""

from __future__ import annotations

import uuid

from django.db import models


class Post(models.Model):
    """A creator's feed post (maps to the frontend ``Post`` type)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
        "creator.Creator",
        on_delete=models.CASCADE,
        related_name="posts",
    )
    body = models.TextField(blank=True, default="")
    media_url = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["creator", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the post."""
        return f"post:{self.id}"


class Comment(models.Model):
    """A comment on a post. ``author_name`` is the display string shown to fans."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        "identity.Account",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="comments",
    )
    author_name = models.CharField(max_length=40, blank=True, default="")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["post", "created_at"]),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        """Identify the comment."""
        return f"comment:{self.id}"


class Like(models.Model):
    """A fan's like on a post. Uniqueness prevents double-like."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    user = models.ForeignKey(
        "identity.Account",
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["post", "user"], name="uniq_like_post_user"),
        ]

    def __str__(self) -> str:
        """Identify the like edge."""
        return f"like:{self.user_id}->{self.post_id}"
