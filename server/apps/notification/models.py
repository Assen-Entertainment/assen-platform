"""Domain models for notification — the in-app notification feed (B4).

``Notification`` is the durable, per-recipient feed shown to fans (like/comment/
follow/order/system). It is distinct from the operator *push* dispatch
(:mod:`apps.notification.services` ``send_notification`` + :mod:`.policy`), which
is a policy-guarded FCM transport with no stored model. Domain triggers append to
this feed via :func:`apps.notification.services.notify`.

Migrated app — ``migrate`` applies ``0001_initial``; regenerate with
``makemigrations`` when models change.
"""

from __future__ import annotations

import uuid

from django.db import models


class NotificationKind(models.TextChoices):
    """Notification categories (drive the web icon/route)."""

    LIKE = "like", "like"
    COMMENT = "comment", "comment"
    FOLLOW = "follow", "follow"
    ORDER = "order", "order"
    SYSTEM = "system", "system"


class Notification(models.Model):
    """One in-app notification for a recipient account (maps to frontend ``Notification``)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        "identity.Account", on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=16, choices=NotificationKind.choices)
    title = models.CharField(max_length=200)
    # Click target (relative path). Empty means non-navigable.
    href = models.CharField(max_length=500, blank=True, default="")
    # Set when the recipient reads it; NULL means unread.
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["recipient", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the notification."""
        return f"notif:{self.recipient_id}:{self.kind}"
