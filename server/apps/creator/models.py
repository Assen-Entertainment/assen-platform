"""Creator profile model (SDLC 09 §3 — creator context, E11/B1).

A ``Creator`` is the public identity fans discover and follow. It optionally
links 1:1 to an :class:`~apps.identity.models.Account` (the user who operates
it); the link is nullable so demo/seed creators can exist before accounts do.

Migrated app — ``migrate`` applies ``0001_initial`` (see
[[assen-server-unmigrated-apps]]); regenerate with ``makemigrations`` when models change.

Follower and post counts are *derived* (annotated at query time from the social
and content relations), not stored, so they cannot drift.
"""

from __future__ import annotations

import uuid

from django.core.validators import RegexValidator
from django.db import models

# URL-safe slug: lowercase letters, digits, and underscore only. Keeps the
# `/creator/{handle}` route round-trippable (no `/`, spaces, or case ambiguity).
_HANDLE_VALIDATOR = RegexValidator(
    r"^[a-z0-9_]+$", "handle는 소문자·숫자·밑줄(_)만 사용할 수 있습니다."
)


class Creator(models.Model):
    """A creator's public profile (maps to the frontend ``Creator`` type)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Stable public slug used in URLs (/creator/{handle}) — the lookup key.
    handle = models.CharField(
        max_length=32, unique=True, db_index=True, validators=[_HANDLE_VALIDATOR]
    )
    name = models.CharField(max_length=80)
    bio = models.TextField(blank=True, default="")
    # Signature accent colour (hex, e.g. "#E14B8A"); empty => platform default.
    accent_color = models.CharField(max_length=9, blank=True, default="")
    avatar_url = models.CharField(max_length=500, blank=True, default="")
    cover_url = models.CharField(max_length=500, blank=True, default="")
    category = models.CharField(max_length=40, blank=True, default="")
    verified = models.BooleanField(default=False)
    # The operating account. 1:1, nullable so seed data can exist accountless.
    owner = models.OneToOneField(
        "identity.Account",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="creator_profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the creator by handle."""
        return f"@{self.handle}"
