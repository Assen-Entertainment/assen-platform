"""Notification policy guard — the allowed-categories allowlist + forbidden guard.

ASS-113 v0 (PRD "알림 정책"; CONSTRAINTS #16 one-way feed+push). The platform may
only emit four categories of notification; anything else is refused *fail-closed*
at the code level. This module is the single source of truth for that policy and
the guard that domain triggers call before any dispatch.

Allowed (PRD 허용 4종):
  - reservation status change
  - event notice
  - coupon issued / expired
  - a favourite cast's **upcoming** attendance summary

Forbidden (PRD 금지 알림 — named, code-level guard):
  - real-time location attendance ("실시간 위치성 출근")
  - "in store now" immediacy / over-engagement
  - high-value payment inducement
  - inducing an expectation of a private reply

The allowlist is the authority: an unknown/unlisted category is refused exactly
like a forbidden one (fail-closed), so a new notification kind cannot ship
without a deliberate policy change here. :data:`FORBIDDEN_NOTIFICATIONS` is
documentation + a precise denial reason for the explicitly-banned kinds.

Two category-agnostic / category-specific data-model rules back the policy:
  - No notification may carry a real-time presence field
    (:func:`assert_no_realtime_presence`) — "지금 매장에 있음" 즉시성 금지.
  - The cast-attendance category may reference only a **future** schedule
    (:func:`assert_cast_schedule_future_only`) — P0_Scope_Reconciliation L80
    makes "실시간 위치성 금지" a data-model rule, not merely a category name.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from django.db import models
from django.utils import timezone


class NotificationCategory(models.TextChoices):
    """The only notification categories the platform may emit (PRD 허용 4종)."""

    RESERVATION_STATUS = "reservation_status", "예약 상태 변경"
    EVENT_NOTICE = "event_notice", "이벤트 공지"
    COUPON = "coupon", "쿠폰 발행·만료"
    FAVORITE_CAST_SCHEDULE = "favorite_cast_schedule", "최애 캐스트 예정 출근 요약"


# The allowlist is the authority: only these values may be dispatched.
ALLOWED_CATEGORIES: frozenset[str] = frozenset(NotificationCategory.values)

# Named forbidden kinds (PRD 금지 알림) — self-documenting and explicitly denied
# with a clear reason. Not an exhaustive list of "everything not allowed"; the
# allowlist already refuses anything unlisted. These give a precise message when a
# caller names one of the policy's explicitly-banned kinds.
FORBIDDEN_NOTIFICATIONS: dict[str, str] = {
    "realtime_location_attendance": "실시간 위치성 출근 알림은 금지됩니다.",
    "in_store_now": "캐스트의 실시간 매장 체류 즉시성 알림은 금지됩니다.",
    "high_value_payment_inducement": "고액 결제 유도 알림은 금지됩니다.",
    "private_reply_expectation": "사적 응답을 기대하게 하는 알림은 금지됩니다.",
}

# Data keys that would smuggle a real-time presence signal through the payload;
# their presence is refused (any category) so the "no real-time location" rule
# cannot be bypassed by moving the signal into ``data``.
REALTIME_PRESENCE_KEYS: frozenset[str] = frozenset(
    {
        "in_store_now",
        "now_at_store",
        "is_present",
        "present_now",
        "current_status",
        "live_location",
        "checked_in_now",
    }
)

# Keys the dispatch service stamps authoritatively (the validated category and, for
# a cast-schedule notice, the future date). A caller may not set them via ``data``
# — they are rejected up front so a caller cannot spoof the category or smuggle a
# non-future date past the future-only guard (the value the service validated must
# be the value that is actually transmitted).
RESERVED_DATA_KEYS: frozenset[str] = frozenset({"category", "scheduled_date"})


class NotificationPolicyError(Exception):
    """Raised when a notification violates the P0 notification policy (fail-closed)."""


def _normalized_keys(data: Mapping[str, object]) -> set[str]:
    """Return the payload's keys folded to canonical form (trimmed, lower-cased).

    Membership guards compare on this canonical form so a forbidden/reserved key
    cannot slip through by casing or surrounding whitespace
    (``In_Store_Now``/``IN_STORE_NOW``/``"scheduled_date "``). It is a denylist, so
    separator variants (e.g. camelCase ``inStoreNow``) are out of scope by design.
    """
    return {str(key).strip().lower() for key in data}


def is_allowed_category(category: str) -> bool:
    """Return whether ``category`` is one of the four allowed categories."""
    return category in ALLOWED_CATEGORIES


def assert_category_allowed(category: str) -> None:
    """Refuse any category outside the allowlist (fail-closed).

    A named-forbidden category gets its specific reason; any other unlisted value
    is refused generically. Either way nothing outside 허용 4종 is dispatchable.
    """
    if category in ALLOWED_CATEGORIES:
        return
    reason = FORBIDDEN_NOTIFICATIONS.get(category)
    if reason is not None:
        raise NotificationPolicyError(reason)
    raise NotificationPolicyError("Notification category is not allowed.")


def assert_no_realtime_presence(data: Mapping[str, object] | None) -> None:
    """Refuse any notification carrying a real-time presence field (any category).

    "지금 매장에 있음" 즉시성/위치성 알림 금지 (PRD) is category-agnostic: no
    notification may smuggle a live-presence signal through its data payload. Keys
    are compared case-insensitively (``In_Store_Now`` does not slip past). The
    offending key is not echoed back (no-echo, ASS-110 lesson).
    """
    if not data:
        return
    if _normalized_keys(data) & REALTIME_PRESENCE_KEYS:
        raise NotificationPolicyError("A notification must not carry a real-time presence field.")


def assert_no_reserved_data_keys(data: Mapping[str, object] | None) -> None:
    """Refuse caller ``data`` that carries a key the service stamps itself.

    ``category`` and ``scheduled_date`` are stamped authoritatively by the dispatch
    service from validated values; a caller-supplied copy (any casing) is rejected
    so it cannot override the validated value (e.g. a past ``scheduled_date`` riding
    out while the future-only guard checked only the parameter).
    """
    if not data:
        return
    if _normalized_keys(data) & RESERVED_DATA_KEYS:
        raise NotificationPolicyError("A notification data payload must not set a reserved key.")


def assert_cast_schedule_future_only(*, scheduled_date: date | None) -> None:
    """The favourite-cast schedule notification may reference only a future date.

    P0_Scope_Reconciliation L80: future-schedule only, which enforces "실시간
    위치성 금지" as a data-model rule. ``scheduled_date`` is required and must be
    strictly after today (store-local).
    """
    if scheduled_date is None:
        raise NotificationPolicyError(
            "A favourite-cast schedule notification requires a future scheduled_date."
        )
    if scheduled_date <= timezone.localdate():
        raise NotificationPolicyError(
            "A favourite-cast schedule notification must reference a future date only."
        )
