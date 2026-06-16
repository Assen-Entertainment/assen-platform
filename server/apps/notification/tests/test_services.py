"""Tests for the notification dispatch service (ASS-113 v0).

Covers: an allowed notification is sent (and its category stamped); a
forbidden/unknown category, a real-time presence field, and an unsafe
cast-schedule date are all refused before the adapter is ever touched (nothing
sent). Uses the in-memory mock adapter — no DB.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.notification.adapters import MockNotificationAdapter
from apps.notification.policy import NotificationPolicyError
from apps.notification.services import send_notification


def test_allowed_notification_is_sent_and_category_stamped() -> None:
    """An allowed category is delivered and the category is stamped on the data."""
    adapter = MockNotificationAdapter()
    result = send_notification(
        category="reservation_status",
        token="device-1",
        title="예약 확정",
        body="예약이 확정되었습니다.",
        adapter=adapter,
        data={"reservation_id": "r1"},
    )
    assert result.accepted is True
    assert len(adapter.sent) == 1
    sent = adapter.sent[0]
    assert sent.token == "device-1"
    assert sent.data["category"] == "reservation_status"
    assert sent.data["reservation_id"] == "r1"


def test_forbidden_category_is_refused_and_nothing_sent() -> None:
    """A named-forbidden category raises and never reaches the adapter."""
    adapter = MockNotificationAdapter()
    with pytest.raises(NotificationPolicyError):
        send_notification(
            category="high_value_payment_inducement",
            token="device-1",
            title="x",
            body="y",
            adapter=adapter,
        )
    assert adapter.sent == []


def test_unknown_category_is_refused_and_nothing_sent() -> None:
    """An unlisted category raises fail-closed and nothing is sent."""
    adapter = MockNotificationAdapter()
    with pytest.raises(NotificationPolicyError):
        send_notification(
            category="surprise_promo",
            token="device-1",
            title="x",
            body="y",
            adapter=adapter,
        )
    assert adapter.sent == []


def test_realtime_presence_field_is_refused_for_any_category() -> None:
    """An allowed category still cannot smuggle a real-time presence field."""
    adapter = MockNotificationAdapter()
    with pytest.raises(NotificationPolicyError):
        send_notification(
            category="event_notice",
            token="device-1",
            title="x",
            body="y",
            adapter=adapter,
            data={"in_store_now": "true"},
        )
    assert adapter.sent == []


def test_cast_schedule_future_date_is_sent_and_stamped() -> None:
    """A favourite-cast schedule with a future date is sent with the date stamped."""
    adapter = MockNotificationAdapter()
    future = timezone.localdate() + timedelta(days=5)
    result = send_notification(
        category="favorite_cast_schedule",
        token="device-1",
        title="예정 출근",
        body="최애의 다음 출근 일정 요약",
        adapter=adapter,
        scheduled_date=future,
    )
    assert result.accepted is True
    assert adapter.sent[0].data["scheduled_date"] == future.isoformat()
    assert adapter.sent[0].data["category"] == "favorite_cast_schedule"


def test_cast_schedule_past_or_today_or_missing_is_refused() -> None:
    """A favourite-cast schedule on today/past or without a date is refused."""
    adapter = MockNotificationAdapter()
    for sched in (timezone.localdate(), timezone.localdate() - timedelta(days=1), None):
        with pytest.raises(NotificationPolicyError):
            send_notification(
                category="favorite_cast_schedule",
                token="device-1",
                title="x",
                body="y",
                adapter=adapter,
                scheduled_date=sched,
            )
    assert adapter.sent == []


def test_caller_cannot_override_scheduled_date_via_data() -> None:
    """A valid future param plus a past data['scheduled_date'] is refused, not sent.

    Closes the guard partial-bypass: the value the policy validated must be the
    value transmitted, so a reserved key in data is rejected outright.
    """
    adapter = MockNotificationAdapter()
    future = timezone.localdate() + timedelta(days=5)
    with pytest.raises(NotificationPolicyError):
        send_notification(
            category="favorite_cast_schedule",
            token="device-1",
            title="x",
            body="y",
            adapter=adapter,
            data={"scheduled_date": "2020-01-01"},
            scheduled_date=future,
        )
    assert adapter.sent == []


def test_caller_cannot_spoof_category_via_data() -> None:
    """A caller-supplied data['category'] (any casing) is refused before send."""
    adapter = MockNotificationAdapter()
    with pytest.raises(NotificationPolicyError):
        send_notification(
            category="event_notice",
            token="device-1",
            title="x",
            body="y",
            adapter=adapter,
            data={"Category": "high_value_payment_inducement"},
        )
    assert adapter.sent == []


def test_realtime_presence_casing_variant_is_refused() -> None:
    """A cased presence key cannot slip through the service either."""
    adapter = MockNotificationAdapter()
    with pytest.raises(NotificationPolicyError):
        send_notification(
            category="event_notice",
            token="device-1",
            title="x",
            body="y",
            adapter=adapter,
            data={"IN_STORE_NOW": "true"},
        )
    assert adapter.sent == []
