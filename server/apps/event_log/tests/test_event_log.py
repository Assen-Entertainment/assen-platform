"""Acceptance tests for the append-only event log and emission contract.

Covers: append-only enforcement (save/update/delete blocked), event-name +
payload validation across all registered events, safety-detail separation, the
20+ event registry, and MSFC / 30-day revisit / operator-exclusion queries.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.event_log.events import (
    EVENT_PAYLOAD_SCHEMAS,
    ActorType,
    EventName,
    EventSource,
)
from apps.event_log.models import AppendOnlyViolation, EventRecord
from apps.event_log.services import (
    EventValidationError,
    count_msfc_starts,
    count_revisits_within,
    emit_event,
    reattribute_anonymous_events,
)

pytestmark = pytest.mark.django_db


def _emit_signup(fan_id: str = "fan-1") -> EventRecord:
    """Emit a minimal valid ``fan_signed_up`` event for reuse in tests."""
    return emit_event(
        event_name=EventName.FAN_SIGNED_UP.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.FAN.value,
        source=EventSource.WEB.value,
        fan_id=fan_id,
        payload={
            "fan_id": fan_id,
            "signup_method": "web",
            "consent_terms": True,
            "consent_privacy": True,
        },
    )


def _checkin(fan_id: str, *, operator: bool = False, verified: bool = True) -> EventRecord:
    """Emit a ``visit_checked_in`` event, defaulting to an MSFC-eligible visit."""
    return emit_event(
        event_name=EventName.VISIT_CHECKED_IN.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value if operator else ActorType.FAN.value,
        source=EventSource.KIOSK.value,
        fan_id=fan_id,
        visit_id=f"visit-{fan_id}",
        actor_is_operator=operator,
        payload={
            "visit_id": f"visit-{fan_id}",
            "store_id": "store-1",
            "business_day": "2026-06-12",
            "visit_type": "first",
            "checkin_method": "qr",
            "is_verified_offline_visit": verified,
        },
    )


# --------------------------------------------------------------------------
# Append-only enforcement
# --------------------------------------------------------------------------


def test_emit_creates_record() -> None:
    """A valid emit persists exactly one row and returns it."""
    record = _emit_signup()
    assert EventRecord.objects.count() == 1
    assert record.event_name == EventName.FAN_SIGNED_UP.value
    assert record.event_id is not None


def test_resaving_existing_record_is_blocked() -> None:
    """Re-saving a persisted event raises (immutable ledger)."""
    record = _emit_signup()
    with pytest.raises(AppendOnlyViolation):
        record.save()


def test_instance_delete_is_blocked() -> None:
    """Deleting an event instance raises."""
    record = _emit_signup()
    with pytest.raises(AppendOnlyViolation):
        record.delete()


def test_queryset_update_is_blocked() -> None:
    """Bulk update via queryset (bypasses save) is blocked."""
    _emit_signup()
    with pytest.raises(AppendOnlyViolation):
        EventRecord.objects.all().update(status="cancelled")


def test_queryset_delete_is_blocked() -> None:
    """Bulk delete via queryset (bypasses delete) is blocked."""
    _emit_signup()
    with pytest.raises(AppendOnlyViolation):
        EventRecord.objects.all().delete()


# --------------------------------------------------------------------------
# Event name + payload validation
# --------------------------------------------------------------------------


def test_unknown_event_name_rejected() -> None:
    """An unregistered event name cannot be emitted."""
    with pytest.raises(EventValidationError):
        emit_event(
            event_name="not_a_real_event",
            occurred_at=timezone.now(),
            actor_type=ActorType.FAN.value,
            source=EventSource.WEB.value,
            payload={},
        )


def test_missing_required_payload_field_rejected() -> None:
    """A payload missing a schema-required field is rejected and nothing is written."""
    with pytest.raises(EventValidationError):
        emit_event(
            event_name=EventName.FAN_SIGNED_UP.value,
            occurred_at=timezone.now(),
            actor_type=ActorType.FAN.value,
            source=EventSource.WEB.value,
            payload={"fan_id": "fan-1"},  # missing signup_method/consent_*
        )
    assert EventRecord.objects.count() == 0


def test_registry_covers_at_least_twenty_events() -> None:
    """The registry encodes the core-20 plus the reconciled additions."""
    assert len(EVENT_PAYLOAD_SCHEMAS) >= 20
    # Reconciliation additions must be present.
    assert EventName.RESERVATION_CREATED.value in EVENT_PAYLOAD_SCHEMAS
    assert EventName.RESERVATION_CANCELLED.value in EVENT_PAYLOAD_SCHEMAS


def test_every_registered_event_emits_with_a_minimal_payload() -> None:
    """Each registered event has a payload that validates — schema sanity sweep.

    Guards against a schema declaring a required field the canonical example
    cannot satisfy, which would make the event un-emittable in production.
    """
    examples = _minimal_payloads()
    for name in EVENT_PAYLOAD_SCHEMAS:
        assert name in examples, f"no example payload for {name}"
        record = emit_event(
            event_name=name,
            occurred_at=timezone.now(),
            actor_type=ActorType.SYSTEM.value,
            source=EventSource.SYSTEM.value,
            payload=examples[name],
        )
        assert record.pk is not None


# --------------------------------------------------------------------------
# Safety-detail separation
# --------------------------------------------------------------------------


def test_safety_event_rejects_report_narrative_in_payload() -> None:
    """A safety event carrying raw report text is rejected (detail separation)."""
    with pytest.raises(EventValidationError):
        emit_event(
            event_name=EventName.SAFETY_REPORT_CREATED.value,
            occurred_at=timezone.now(),
            actor_type=ActorType.OPERATOR.value,
            source=EventSource.ADMIN.value,
            actor_is_operator=True,
            payload={
                "safety_report_id": "sr-1",
                "reporter_type": "fan",
                "target_type": "fan",
                "report_type": "verbal_abuse",
                "severity": "high",
                "visibility": "manager_only",
                "report_text": "the full narrative that must not be stored here",
            },
        )


def test_safety_event_without_narrative_is_accepted() -> None:
    """Classification-only safety event persists."""
    record = emit_event(
        event_name=EventName.SAFETY_REPORT_CREATED.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.ADMIN.value,
        actor_is_operator=True,
        payload={
            "safety_report_id": "sr-1",
            "reporter_type": "fan",
            "target_type": "fan",
            "report_type": "verbal_abuse",
            "severity": "high",
            "visibility": "manager_only",
        },
    )
    assert record.payload["severity"] == "high"
    assert "report_text" not in record.payload


# --------------------------------------------------------------------------
# MSFC / 30-day revisit / operator exclusion
# --------------------------------------------------------------------------


def test_msfc_counts_verified_visits_and_excludes_operators() -> None:
    """MSFC starts count verified fan visits and drop operator/unverified ones."""
    _checkin("fan-a")
    _checkin("fan-b")
    _checkin("op-1", operator=True)  # operator -> excluded
    _checkin("fan-c", verified=False)  # not verified -> excluded

    assert count_msfc_starts(exclude_operators=True) == 2
    # Without exclusion the operator visit is counted too (still verified).
    assert count_msfc_starts(exclude_operators=False) == 3


def test_anonymous_visit_is_not_an_msfc_start_until_merged() -> None:
    """A visit with no fan_id is excluded from MSFC; merge links the history."""
    emit_event(
        event_name=EventName.VISIT_CHECKED_IN.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.FAN.value,
        source=EventSource.KIOSK.value,
        ids={"anonymous_id": "anon-1"},
        payload={
            "visit_id": "visit-anon",
            "store_id": "store-1",
            "business_day": "2026-06-12",
            "visit_type": "first",
            "checkin_method": "temporary",
            "is_verified_offline_visit": True,
        },
    )
    assert count_msfc_starts() == 0  # anonymous, no fan_id

    linked = reattribute_anonymous_events(anonymous_id="anon-1", fan_id="fan-merged")
    assert linked == 1  # the prior anonymous visit was found and linked
    # The merge does not retroactively rewrite the old row's fan_id, so MSFC
    # still sees zero double-counted starts from the anonymous visit.
    assert count_msfc_starts() == 0


def test_revisit_within_30_days_counts_repeat_fans() -> None:
    """A fan with two completed visits in the window counts once as a revisit."""
    now = timezone.now()
    for fan, when in [
        ("fan-x", now - timedelta(days=20)),
        ("fan-x", now - timedelta(days=2)),  # repeat within 30d
        ("fan-y", now - timedelta(days=1)),  # single visit
    ]:
        emit_event(
            event_name=EventName.VISIT_COMPLETED.value,
            occurred_at=when,
            actor_type=ActorType.FAN.value,
            source=EventSource.KIOSK.value,
            fan_id=fan,
            visit_id=f"v-{fan}-{when.timestamp()}",
            payload={
                "fan_id": fan,
                "visit_id": f"v-{fan}-{when.timestamp()}",
                "completed_at": when.isoformat(),
                "has_payment_reference": True,
            },
        )
    assert count_revisits_within(days=30) == 1


def _minimal_payloads() -> dict[str, dict[str, object]]:
    """Return a minimal valid payload for every registered event name."""
    return {
        EventName.FAN_SIGNED_UP.value: {
            "fan_id": "f",
            "signup_method": "web",
            "consent_terms": True,
            "consent_privacy": True,
        },
        EventName.ANONYMOUS_USER_CREATED.value: {"anonymous_id": "a"},
        EventName.ANONYMOUS_USER_MERGED.value: {"anonymous_id": "a", "fan_id": "f"},
        EventName.RULE_CONSENT_GIVEN.value: {
            "fan_id": "f",
            "consent_kind": "rule",
            "consent_version": "1",
        },
        EventName.RESERVATION_CREATED.value: {"fan_id": "f", "reservation_id": "r"},
        EventName.RESERVATION_CANCELLED.value: {"fan_id": "f", "reservation_id": "r"},
        EventName.VISIT_CHECKED_IN.value: {
            "visit_id": "v",
            "store_id": "s",
            "business_day": "2026-06-12",
            "visit_type": "first",
            "checkin_method": "qr",
            "is_verified_offline_visit": True,
        },
        EventName.VISIT_COMPLETED.value: {
            "fan_id": "f",
            "visit_id": "v",
            "completed_at": "2026-06-12T00:00:00Z",
            "has_payment_reference": True,
        },
        EventName.VISIT_INVALIDATED.value: {
            "visit_id": "v",
            "reason": "duplicate",
        },
        EventName.CAST_PROFILE_VIEWED.value: {"cast_id": "c"},
        EventName.SCHEDULE_VIEWED.value: {
            "store_id": "s",
            "business_day": "2026-06-12",
            "viewed_for_date": "2026-06-12",
            "view_scope": "day",
            "source_surface": "home",
        },
        EventName.FAVORITE_ADDED.value: {
            "fan_id": "f",
            "cast_id": "c",
            "favorite_source": "profile",
        },
        EventName.FAVORITE_REMOVED.value: {"fan_id": "f", "cast_id": "c"},
        EventName.CHEKI_RECORDED.value: {
            "visit_id": "v",
            "cast_id": "c",
            "cheki_id": "ch",
            "cheki_type": "basic",
            "quantity": 1,
            "image_stored": True,
        },
        EventName.CHEKI_INVALIDATED.value: {
            "cheki_id": "ch",
            "reason": "duplicate",
        },
        EventName.EVENT_VIEWED.value: {"event_campaign_id": "e"},
        EventName.EVENT_RESERVED.value: {
            "fan_id": "f",
            "event_campaign_id": "e",
            "reservation_id": "r",
            "event_type": "birthday",
            "reservation_status": "reserved",
        },
        EventName.COUPON_ISSUED.value: {
            "fan_id": "f",
            "coupon_id": "co",
            "coupon_type": "revisit",
        },
        EventName.COUPON_REDEEMED.value: {
            "fan_id": "f",
            "coupon_id": "co",
            "coupon_redemption_id": "cr",
            "coupon_type": "revisit",
            "redemption_status": "redeemed",
        },
        EventName.POS_ORDER_LINKED.value: {
            "visit_id": "v",
            "link_method": "manual",
            "payment_status": "paid",
            "linked_confidence": "manual",
        },
        EventName.POS_RECONCILIATION_FLAGGED.value: {
            "business_day": "2026-06-12",
            "mismatch_reason": "amount_mismatch",
        },
        EventName.PAYMENT_REFUNDED.value: {
            "refund_type": "full",
            "refund_reason": "customer_request",
        },
        EventName.SAFETY_REPORT_CREATED.value: {
            "safety_report_id": "sr",
            "reporter_type": "fan",
            "target_type": "fan",
            "report_type": "other",
            "severity": "low",
            "visibility": "restricted",
        },
        EventName.SAFETY_REPORT_RESOLVED.value: {
            "safety_report_id": "sr",
            "resolution": "closed",
        },
        EventName.USER_BLOCKED.value: {
            "block_id": "b",
            "block_scope": "all",
            "block_reason": "safety_risk",
            "effective_from": "2026-06-12T00:00:00Z",
        },
        EventName.ADMIN_NOTE_CREATED.value: {"note_id": "n"},
    }
