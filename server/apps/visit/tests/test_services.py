"""Acceptance tests for visit service side effects.

These prove the ASS-94 contract: manual check-in and void emit the *canonical*
registered events through ``emit_event`` (so the payload validates and MSFC sees
them), a genuine fan visit is not flagged as excluded operator traffic, and a
metadata correction touches the audit log only.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEntry
from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.event_log.services import count_msfc_starts
from apps.identity.models import Account, Role
from apps.visit.models import VisitRecordStatus
from apps.visit.services import correct_visit, record_visit, void_visit

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def test_record_visit_emits_canonical_checked_in_event() -> None:
    """Manual check-in persists the visit plus audit and a visit_checked_in event."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    visited_at = timezone.now()

    record = record_visit(
        fan=fan,
        visited_at=visited_at,
        note="first stamp",
        actor=operator,
    )

    assert record.fan_id == fan.pk
    audit = AuditEntry.objects.get(action=AuditAction.VISIT_RECORDED.value)
    assert audit.actor_id == operator.pk

    event = EventRecord.objects.get(event_name=EventName.VISIT_CHECKED_IN.value)
    assert event.visit_id == str(record.id)
    assert event.fan_id == str(fan.fan_id)
    # The load-bearing fix: a real fan visit recorded by an operator must count
    # toward MSFC, so it is NOT flagged as excluded operator/test traffic.
    assert event.actor_is_operator is False
    assert event.payload["visit_type"] == "manual"
    assert event.payload["checkin_method"] == "operator"
    assert event.payload["is_verified_offline_visit"] is True
    assert event.payload["store_id"] == record.store_id
    assert event.payload["business_day"]


def test_correct_visit_writes_audit_only_no_event() -> None:
    """A metadata correction records before/after audit and emits no new event."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    record = record_visit(fan=fan, visited_at=timezone.now(), actor=operator)
    new_time = timezone.now() + timedelta(minutes=5)

    corrected = correct_visit(
        record,
        visited_at=new_time,
        note="corrected minute",
        actor=operator,
    )

    assert corrected.note == "corrected minute"
    audit = AuditEntry.objects.get(action=AuditAction.VISIT_CORRECTED.value)
    assert audit.metadata["before"]["note"] == ""
    assert audit.metadata["after"]["note"] == "corrected minute"
    # Correction is operational, not analytics: only the original check-in event
    # exists; no visit_corrected event is invented.
    assert EventRecord.objects.count() == 1
    assert EventRecord.objects.filter(
        event_name=EventName.VISIT_CHECKED_IN.value
    ).exists()


def test_void_visit_emits_invalidated_and_rejects_second_void() -> None:
    """Voiding flips status, emits visit_invalidated, and blocks a re-void."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    record = record_visit(fan=fan, visited_at=timezone.now(), actor=operator)

    voided = void_visit(record=record, reason="duplicate POS row", actor=operator)

    assert voided.status == VisitRecordStatus.VOIDED.value
    assert voided.void_reason == "duplicate POS row"
    audit = AuditEntry.objects.get(action=AuditAction.VISIT_VOIDED.value)
    assert audit.reason == "duplicate POS row"

    event = EventRecord.objects.get(event_name=EventName.VISIT_INVALIDATED.value)
    assert event.visit_id == str(record.id)
    assert event.payload["reason"] == "duplicate POS row"

    with pytest.raises(ValueError):
        void_visit(record=voided, reason="second reason", actor=operator)


def test_void_visit_requires_reason() -> None:
    """An empty void reason is rejected so every void carries accountability."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    record = record_visit(fan=fan, visited_at=timezone.now(), actor=operator)

    with pytest.raises(ValueError):
        void_visit(record=record, reason="   ", actor=operator)


def test_voided_visit_excluded_from_msfc() -> None:
    """Voiding removes the visit from MSFC via the visit_invalidated event.

    Proves the canonical "visit_invalidated → 제외" contract is actually wired:
    a manual check-in counts as an MSFC start, and voiding it drops the count
    even though the append-only check-in row is never mutated.
    """
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    record = record_visit(fan=fan, visited_at=timezone.now(), actor=operator)
    assert count_msfc_starts() == 1

    void_visit(record=record, reason="duplicate POS row", actor=operator)
    assert count_msfc_starts() == 0
