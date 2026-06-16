"""Tests for the notification policy guard (ASS-113 v0).

Covers: the allowlist is exactly the four PRD categories; a named-forbidden and an
unknown category are both refused fail-closed; no notification may carry a
real-time presence field; and the favourite-cast schedule is future-only. Pure
in-memory policy — no DB.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.notification.policy import (
    ALLOWED_CATEGORIES,
    FORBIDDEN_NOTIFICATIONS,
    REALTIME_PRESENCE_KEYS,
    RESERVED_DATA_KEYS,
    NotificationCategory,
    NotificationPolicyError,
    assert_cast_schedule_future_only,
    assert_category_allowed,
    assert_no_realtime_presence,
    assert_no_reserved_data_keys,
    is_allowed_category,
)


def test_allowlist_is_exactly_the_four_prd_categories() -> None:
    """The allowlist matches the four allowed categories and nothing else."""
    assert ALLOWED_CATEGORIES == {
        "reservation_status",
        "event_notice",
        "coupon",
        "favorite_cast_schedule",
    }
    assert len(ALLOWED_CATEGORIES) == 4


@pytest.mark.parametrize("category", sorted(ALLOWED_CATEGORIES))
def test_allowed_categories_pass(category: str) -> None:
    """Each allowed category passes the guard and reads as allowed."""
    assert is_allowed_category(category) is True
    assert_category_allowed(category)  # does not raise


@pytest.mark.parametrize("category", sorted(FORBIDDEN_NOTIFICATIONS))
def test_named_forbidden_categories_are_refused(category: str) -> None:
    """A named-forbidden category is refused with its specific reason."""
    assert is_allowed_category(category) is False
    with pytest.raises(NotificationPolicyError) as exc:
        assert_category_allowed(category)
    assert str(exc.value) == FORBIDDEN_NOTIFICATIONS[category]


def test_unknown_category_is_refused_fail_closed() -> None:
    """An unlisted category is refused generically (fail-closed)."""
    assert is_allowed_category("totally_made_up") is False
    with pytest.raises(NotificationPolicyError):
        assert_category_allowed("totally_made_up")


def test_empty_category_is_refused() -> None:
    """An empty category string is refused (fail-closed)."""
    with pytest.raises(NotificationPolicyError):
        assert_category_allowed("")


@pytest.mark.parametrize("key", sorted(REALTIME_PRESENCE_KEYS))
def test_every_realtime_presence_key_is_refused(key: str) -> None:
    """Every key in REALTIME_PRESENCE_KEYS is refused, for any category."""
    with pytest.raises(NotificationPolicyError):
        assert_no_realtime_presence({key: "true"})


@pytest.mark.parametrize("variant", ["In_Store_Now", "IN_STORE_NOW", " in_store_now "])
def test_realtime_presence_guard_is_case_and_whitespace_insensitive(variant: str) -> None:
    """A presence key cannot slip past by casing or surrounding whitespace."""
    with pytest.raises(NotificationPolicyError):
        assert_no_realtime_presence({variant: "true"})


def test_clean_payload_passes_realtime_guard() -> None:
    """A payload without any presence key passes; None/empty are no-ops."""
    assert_no_realtime_presence(None)
    assert_no_realtime_presence({})
    assert_no_realtime_presence({"coupon_id": "abc", "event_id": "e1"})


@pytest.mark.parametrize("key", ["scheduled_date", "category", "Scheduled_Date", "CATEGORY"])
def test_reserved_data_keys_are_refused(key: str) -> None:
    """A caller cannot set a service-stamped key via data (any casing)."""
    assert key.strip().lower() in RESERVED_DATA_KEYS
    with pytest.raises(NotificationPolicyError):
        assert_no_reserved_data_keys({key: "x"})


def test_non_reserved_data_keys_pass() -> None:
    """Ordinary data keys are allowed; None/empty are no-ops."""
    assert_no_reserved_data_keys(None)
    assert_no_reserved_data_keys({})
    assert_no_reserved_data_keys({"coupon_id": "abc"})


def test_cast_schedule_requires_future_date() -> None:
    """A future date passes; today, past, and missing all raise."""
    future = timezone.localdate() + timedelta(days=3)
    assert_cast_schedule_future_only(scheduled_date=future)  # does not raise

    with pytest.raises(NotificationPolicyError):
        assert_cast_schedule_future_only(scheduled_date=timezone.localdate())
    with pytest.raises(NotificationPolicyError):
        assert_cast_schedule_future_only(scheduled_date=timezone.localdate() - timedelta(days=1))
    with pytest.raises(NotificationPolicyError):
        assert_cast_schedule_future_only(scheduled_date=None)


def test_category_labels_are_present() -> None:
    """Every allowed category carries a human label (for the policy registry)."""
    for choice in NotificationCategory:
        assert choice.label
