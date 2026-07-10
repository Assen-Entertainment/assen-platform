"""Operator API for the notification policy guard (ASS-113 v0).

Two endpoints under ``/api/operator/notifications`` (``operator_required``):
  - ``GET /policy`` — the self-documenting policy registry (allowed 4 + the named
    forbidden kinds), so the guard's rules are inspectable.
  - ``POST /dispatch`` — dispatch one notification; the policy guard runs first,
    so a forbidden/unknown category, a real-time presence field, or an unsafe
    cast-schedule date is refused (422) and never sent. v0 uses the in-memory mock
    adapter (no real FCM yet — that transport lands in P5).

#26 비차단: reuses ``operator_required`` (existing staff RBAC); issues no token and
does not touch auth/session code.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from django.http import HttpRequest
from django.utils import timezone
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import operator_required
from apps.identity.auth import authed, fan_auth
from apps.notification.adapters import MockNotificationAdapter, NotificationAdapter
from apps.notification.models import Notification
from apps.notification.policy import (
    FORBIDDEN_NOTIFICATIONS,
    NotificationCategory,
    NotificationPolicyError,
)
from apps.notification.services import send_notification
from config.api import api
from config.pagination import paginate
from config.throttle import user_write_throttle

notification_router = Router(auth=operator_required, tags=["operator-notification"])

_TEXT_MAX = 500
_DATA_MAX_KEYS = 20
_KEY_MAX = 100


def _adapter() -> NotificationAdapter:
    """Return the push adapter. P0/dev uses the in-memory mock (no real FCM).

    Mirrors ``apps.identity.api._otp_sender`` — a single seam so the real FCM
    transport can be injected in P5 without touching callers.
    """
    return MockNotificationAdapter()


class NotificationError(Schema):
    """Stable error shape for notification endpoints."""

    detail: str


class PolicyCategoryOut(Schema):
    """One allowed category: its code + human label."""

    value: str
    label: str


class ForbiddenOut(Schema):
    """One explicitly-forbidden notification kind: its code + reason."""

    value: str
    reason: str


class PolicyOut(Schema):
    """The notification policy: the allowed 4 + the named forbidden kinds."""

    allowed: list[PolicyCategoryOut]
    forbidden: list[ForbiddenOut]


class DispatchIn(Schema):
    """Operator payload to dispatch one notification (policy-guarded)."""

    category: str = Field(max_length=_TEXT_MAX)
    token: str = Field(min_length=1, max_length=_TEXT_MAX)
    title: str = Field(max_length=_TEXT_MAX)
    body: str = Field(max_length=_TEXT_MAX)
    data: dict[str, str] = Field(default_factory=dict)
    scheduled_date: date | None = None


class DispatchOut(Schema):
    """Result of a dispatch attempt."""

    accepted: bool
    message_id: str
    category: str


@notification_router.get("/policy", response=PolicyOut)
def get_policy(request: HttpRequest) -> PolicyOut:
    """Return the notification policy registry (allowed 4 + forbidden kinds)."""
    del request
    allowed = [
        PolicyCategoryOut(value=choice.value, label=choice.label) for choice in NotificationCategory
    ]
    forbidden = [
        ForbiddenOut(value=value, reason=reason)
        for value, reason in FORBIDDEN_NOTIFICATIONS.items()
    ]
    return PolicyOut(allowed=allowed, forbidden=forbidden)


@notification_router.post("/dispatch", response={200: DispatchOut, 422: NotificationError})
def dispatch_notification(
    request: HttpRequest, payload: DispatchIn
) -> tuple[int, DispatchOut | NotificationError]:
    """Dispatch one notification after the policy guard passes (else 422)."""
    del request
    if len(payload.data) > _DATA_MAX_KEYS:
        return 422, NotificationError(detail="Too many data keys.")
    # Bound each data key/value too (the scalar fields are capped via Field; keep
    # the map symmetric so a 20-key payload cannot smuggle arbitrarily large blobs).
    if any(len(k) > _KEY_MAX or len(v) > _TEXT_MAX for k, v in payload.data.items()):
        return 422, NotificationError(detail="A data key or value is too long.")
    try:
        result = send_notification(
            category=payload.category,
            token=payload.token,
            title=payload.title,
            body=payload.body,
            adapter=_adapter(),
            data=payload.data,
            scheduled_date=payload.scheduled_date,
        )
    except NotificationPolicyError as exc:
        return 422, NotificationError(detail=str(exc))
    # payload.category equals the stamped category: the fail-closed allowlist is an
    # exact match (no normalisation), so the validated input is the stamped value.
    return 200, DispatchOut(
        accepted=result.accepted,
        message_id=result.message_id,
        category=payload.category,
    )


api.add_router("/operator/notifications", notification_router)


# --------------------------------------------------------------------------- #
# Fan surface — the in-app notification feed (B4)
# --------------------------------------------------------------------------- #
fan_notifications_router = Router(auth=fan_auth, tags=["notification"])


class NotificationOut(Schema):
    """One in-app notification (maps to the frontend ``Notification`` type)."""

    id: uuid.UUID
    kind: str
    title: str
    href: str
    read: bool
    created_at: datetime


class NotificationPage(Schema):
    """One page of the fan's notifications plus the next cursor."""

    items: list[NotificationOut]
    next_cursor: str | None = None


class ReadAllOut(Schema):
    """Result of marking every notification read: how many changed."""

    updated: int


def _notification_out(notification: Notification) -> NotificationOut:
    """Build the notification response."""
    return NotificationOut(
        id=notification.id,
        kind=notification.kind,
        title=notification.title,
        href=notification.href,
        read=notification.read_at is not None,
        created_at=notification.created_at,
    )


@fan_notifications_router.get("", response=NotificationPage)
def list_notifications(
    request: HttpRequest, cursor: str | None = None, limit: int | None = None
) -> NotificationPage:
    """List the requesting fan's own notifications, newest first, cursor-paginated."""
    account = authed(request)
    queryset = Notification.objects.filter(recipient=account).order_by("-created_at", "id")
    items, next_cursor = paginate(queryset, cursor=cursor, limit=limit)
    return NotificationPage(
        items=[_notification_out(n) for n in items], next_cursor=next_cursor
    )


@fan_notifications_router.post(
    "/read-all", response=ReadAllOut,
    throttle=user_write_throttle("30/min"),
)
def mark_all_read(request: HttpRequest) -> ReadAllOut:
    """Mark all of the requesting fan's unread notifications as read."""
    account = authed(request)
    updated = Notification.objects.filter(recipient=account, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    return ReadAllOut(updated=updated)


@fan_notifications_router.post(
    "/{notification_id}/read", response={200: NotificationOut, 404: NotificationError},
    throttle=user_write_throttle("60/min"),
)
def mark_read(
    request: HttpRequest, notification_id: uuid.UUID
) -> tuple[int, NotificationOut | NotificationError]:
    """Mark one of the fan's own notifications read (404 if not theirs)."""
    account = authed(request)
    notification = Notification.objects.filter(
        id=notification_id, recipient=account
    ).first()
    if notification is None:
        return 404, NotificationError(detail="알림을 찾을 수 없어요.")
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return 200, _notification_out(notification)


api.add_router("/notifications", fan_notifications_router)
