"""Acceptance tests for cheki service side effects.

Proves the ASS-95 contract: record/void emit the canonical registered events
(``cheki_recorded`` / ``cheki_invalidated``) through ``emit_event``, a genuine
operator-recorded cheki is not flagged as excluded traffic, test cheki and voids
are settlement-excluded, and a metadata correction touches the audit log only.
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEntry
from apps.cheki.models import ChekiRecordStatus, ChekiSettlementStatus
from apps.cheki.services import correct_cheki, record_cheki, void_cheki
from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account, Role
from apps.visit.models import VisitRecord, VisitRecordStatus

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _visit(fan: Account, operator: Account) -> VisitRecord:
    """Create a bare visit row for a cheki to attach to."""
    return VisitRecord.objects.create(
        fan=fan,
        visited_at=timezone.now(),
        created_by=operator,
    )


def test_record_cheki_emits_canonical_event() -> None:
    """Recording a cheki persists the row plus audit and a cheki_recorded event."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    visit = _visit(fan, operator)

    record = record_cheki(
        visit=visit,
        cast_id="mio",
        cheki_type="basic",
        quantity=2,
        actor=operator,
    )

    assert record.settlement_status == ChekiSettlementStatus.CANDIDATE.value
    AuditEntry.objects.get(action=AuditAction.CHEKI_RECORDED.value)
    event = EventRecord.objects.get(event_name=EventName.CHEKI_RECORDED.value)
    assert event.payload["cheki_id"] == str(record.id)
    assert event.payload["cast_id"] == "mio"
    assert event.payload["quantity"] == 2
    assert event.actor_is_operator is False


def test_test_cheki_is_settlement_excluded() -> None:
    """A cheki_type=test row is born settlement-excluded (never counts as sales)."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    visit = _visit(fan, operator)

    record = record_cheki(
        visit=visit,
        cast_id="mio",
        cheki_type="test",
        quantity=1,
        actor=operator,
    )

    assert record.settlement_status == ChekiSettlementStatus.EXCLUDED.value


def test_correct_cheki_writes_audit_only_no_event() -> None:
    """A metadata correction records before/after audit and emits no new event."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    visit = _visit(fan, operator)
    record = record_cheki(
        visit=visit, cast_id="mio", cheki_type="basic", quantity=1, actor=operator
    )

    corrected = correct_cheki(record, quantity=3, actor=operator)

    assert corrected.quantity == 3
    audit = AuditEntry.objects.get(action=AuditAction.CHEKI_CORRECTED.value)
    assert audit.metadata["before"]["quantity"] == 1
    assert audit.metadata["after"]["quantity"] == 3
    # Only the original cheki_recorded event exists; no cheki_corrected invented.
    assert EventRecord.objects.count() == 1


def test_void_cheki_emits_invalidated_and_rejects_second_void() -> None:
    """Voiding flips status + settlement, emits cheki_invalidated, blocks re-void."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    visit = _visit(fan, operator)
    record = record_cheki(
        visit=visit, cast_id="mio", cheki_type="basic", quantity=1, actor=operator
    )

    voided = void_cheki(record=record, reason="duplicate", actor=operator)

    assert voided.status == ChekiRecordStatus.VOIDED.value
    assert voided.settlement_status == ChekiSettlementStatus.EXCLUDED.value
    AuditEntry.objects.get(action=AuditAction.CHEKI_VOIDED.value)
    event = EventRecord.objects.get(event_name=EventName.CHEKI_INVALIDATED.value)
    assert event.payload["cheki_id"] == str(record.id)
    assert event.payload["reason"] == "duplicate"

    with pytest.raises(ValueError):
        void_cheki(record=voided, reason="again", actor=operator)


def test_void_cheki_requires_reason() -> None:
    """An empty void reason is rejected so every void carries accountability."""
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    visit = _visit(fan, operator)
    record = record_cheki(
        visit=visit, cast_id="mio", cheki_type="basic", quantity=1, actor=operator
    )

    with pytest.raises(ValueError):
        void_cheki(record=record, reason="  ", actor=operator)


def test_record_cheki_rejects_voided_visit() -> None:
    """A cheki cannot be recorded against a voided visit (settlement-leak guard)."""
    operator = _account(Role.OPERATOR.value)
    visit = VisitRecord.objects.create(
        fan=_account(Role.FAN.value),
        visited_at=timezone.now(),
        status=VisitRecordStatus.VOIDED.value,
        created_by=operator,
    )

    with pytest.raises(ValueError):
        record_cheki(
            visit=visit,
            cast_id="mio",
            cheki_type="basic",
            quantity=1,
            actor=operator,
        )
