"""Notification dispatch — runs the policy guard, then sends via the adapter.

ASS-113 v0. Domain triggers (reservation status change, coupon issue/expiry,
event notice, favourite-cast schedule summary) call :func:`send_notification`; it
refuses anything :mod:`apps.notification.policy` does not allow *before* the
transport is ever touched, so a forbidden notification can never leave the
platform. The transport is the injected :class:`NotificationAdapter`
(``MockNotificationAdapter`` in P0/dev/tests; real FCM in P5), keeping send logic
out of the domain and honouring CONSTRAINTS #16 (one-way feed+push).

v0 has no durable notification model or event (Data_Event_Schema defines no
notification event; models land in P4/P5 per CONSTRAINTS #38): the guard +
dispatch boundary is the deliverable. Copy content (title/body) is supplied by
callers and reviewed under the UI/UX copy constraints — out of v0.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from apps.identity.models import Account
from apps.notification.adapters import NotificationAdapter, PushMessage, SendResult
from apps.notification.models import Notification
from apps.notification.policy import (
    NotificationCategory,
    assert_cast_schedule_future_only,
    assert_category_allowed,
    assert_no_realtime_presence,
    assert_no_reserved_data_keys,
)


def send_notification(
    *,
    category: str,
    token: str,
    title: str,
    body: str,
    adapter: NotificationAdapter,
    data: Mapping[str, str] | None = None,
    scheduled_date: date | None = None,
) -> SendResult:
    """Dispatch one push after the policy guard passes; raise on any violation.

    Order matters: the policy is checked *before* the adapter is touched, so a
    forbidden/unknown category, a reserved key in ``data``, a real-time presence
    field, or an unsafe cast-schedule date is refused fail-closed and never sent.
    The category (and, for a cast-schedule notice, the future date) is then stamped
    authoritatively — overwriting, not deferring to caller ``data`` — so the value
    the policy validated is exactly the value transmitted.

    Raises:
        NotificationPolicyError: if the notification violates the P0 policy.
    """
    assert_category_allowed(category)
    payload: dict[str, str] = dict(data or {})
    assert_no_reserved_data_keys(payload)
    assert_no_realtime_presence(payload)
    if category == NotificationCategory.FAVORITE_CAST_SCHEDULE.value:
        assert_cast_schedule_future_only(scheduled_date=scheduled_date)
        # scheduled_date is guaranteed non-None by the guard above; stamp the
        # validated value authoritatively (the caller cannot have set this key).
        if scheduled_date is not None:
            payload["scheduled_date"] = scheduled_date.isoformat()
    payload["category"] = category
    message = PushMessage(token=token, title=title, body=body, data=payload)
    return adapter.send(message)


def notify(recipient: Account, kind: str, title: str, href: str = "") -> Notification:
    """Append one notification to a recipient's in-app feed (B4).

    Domain triggers (order placed, follow, comment, …) call this to add to the
    fan's durable notification feed (:class:`~apps.notification.models.Notification`).
    This is separate from :func:`send_notification`, the policy-guarded push
    transport — notify only records the in-app row; a later stitch step wires push.
    """
    return Notification.objects.create(
        recipient=recipient, kind=kind, title=title, href=href
    )
