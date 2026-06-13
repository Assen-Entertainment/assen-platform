"""Acceptance test: anonymous->fan merge does not double-count MSFC.

Staged identity links pre-signup anonymous activity to a fan without rewriting
the append-only log, so the same physical visit is never counted twice as an
MSFC start (Data_Event_Schema L764-769).
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.models import EventRecord
from apps.event_log.services import count_msfc_starts, emit_event
from apps.identity.models import Account, AnonymousSession, Role
from apps.identity.services import merge_anonymous_into_account

pytestmark = pytest.mark.django_db


def _anonymous_verified_visit(anonymous_id: str) -> EventRecord:
    """Emit a verified offline visit attributed only to an anonymous id."""
    return emit_event(
        event_name=EventName.VISIT_CHECKED_IN.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.FAN.value,
        source=EventSource.KIOSK.value,
        ids={"anonymous_id": anonymous_id},
        payload={
            "visit_id": f"visit-{anonymous_id}",
            "store_id": "store-1",
            "business_day": "2026-06-12",
            "visit_type": "first",
            "checkin_method": "temporary",
            "is_verified_offline_visit": True,
        },
    )


def test_merge_links_history_without_double_counting_msfc() -> None:
    """Pre-merge anonymous visit + post-merge fan visit count as one MSFC start each."""
    anon = AnonymousSession.objects.create()
    anon_id = str(anon.anonymous_id)

    # Pre-signup verified visit: not an MSFC start (no fan_id yet).
    _anonymous_verified_visit(anon_id)
    assert count_msfc_starts() == 0

    account = Account.objects.create(role=Role.FAN.value)

    # Merge records anonymous_user_merged and links the prior anonymous event.
    linked = merge_anonymous_into_account(anonymous_id=anon_id, account=account)
    assert linked == 1

    # The anonymous session now points at the account.
    anon.refresh_from_db()
    assert anon.merged_into_id == account.pk

    # Merge itself must not have manufactured an MSFC start: the historical
    # anonymous row still has no fan_id, so it is not retroactively a start.
    assert count_msfc_starts() == 0

    # A genuine post-merge verified visit by the fan is exactly one start.
    emit_event(
        event_name=EventName.VISIT_CHECKED_IN.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.FAN.value,
        source=EventSource.KIOSK.value,
        fan_id=str(account.fan_id),
        visit_id="visit-post-merge",
        payload={
            "visit_id": "visit-post-merge",
            "store_id": "store-1",
            "business_day": "2026-06-12",
            "visit_type": "repeat",
            "checkin_method": "qr",
            "is_verified_offline_visit": True,
        },
    )
    assert count_msfc_starts() == 1  # exactly one, no double count


def test_operator_account_is_flagged_for_metric_exclusion() -> None:
    """Staff accounts report as operator accounts so MSFC can drop them (#1)."""
    fan = Account.objects.create(role=Role.FAN.value)
    operator = Account.objects.create(role=Role.OPERATOR.value)
    admin = Account.objects.create(role=Role.ADMIN.value)

    assert fan.is_operator_account is False
    assert operator.is_operator_account is True
    assert admin.is_operator_account is True
