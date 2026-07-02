"""Service tests for operator schedule management (ASS-93).

Key behaviours: draft entries edit directly; published entries change only via an
approved request; approval is blocked for the requester (separation of duties);
every mutation audits; entries are unpublished, never deleted.
"""

from __future__ import annotations

from datetime import date, time

import pytest

from apps.audit.models import AuditAction, AuditEntry
from apps.identity.models import Account, Role
from apps.schedule.models import (
    ChangeRequestStatus,
    ScheduleEntry,
    ScheduleStatus,
)
from apps.schedule.services import (
    approve_change,
    create_entry,
    edit_draft,
    publish_entry,
    reject_change,
    request_change,
    unpublish_entry,
)

pytestmark = pytest.mark.django_db


def _op() -> Account:
    """Create an operator account."""
    return Account.objects.create(role=Role.OPERATOR.value)


def _entry(actor: Account, *, published: bool = False) -> ScheduleEntry:
    """Create an entry, optionally published."""
    entry = create_entry(
        work_date=date(2026, 6, 20),
        cast_id="mio",
        start_time=time(18, 0),
        end_time=time(22, 0),
        actor=actor,
    )
    if published:
        publish_entry(entry, actor=actor)
    return entry


def test_create_is_draft_and_audited() -> None:
    """A new entry is draft and writes a SCHEDULE_CREATED audit."""
    op = _op()
    entry = _entry(op)
    assert entry.status == ScheduleStatus.DRAFT.value
    AuditEntry.objects.get(action=AuditAction.SCHEDULE_CREATED.value)


def test_edit_draft_then_blocked_after_publish() -> None:
    """Draft edits directly; a published entry rejects direct edit."""
    op = _op()
    entry = _entry(op)
    edit_draft(entry, actor=op, note="updated")
    assert entry.note == "updated"
    AuditEntry.objects.get(action=AuditAction.SCHEDULE_EDITED.value)

    publish_entry(entry, actor=op)
    with pytest.raises(ValueError):
        edit_draft(entry, actor=op, note="nope")


def test_request_change_requires_published() -> None:
    """Change requests apply to published entries only."""
    op = _op()
    draft = _entry(op)
    with pytest.raises(ValueError):
        request_change(entry=draft, proposed={"note": "x"}, reason="r", actor=op)


def test_request_change_rejects_unparseable_value() -> None:
    """A bad date/time is rejected at request time, not deferred to approval."""
    op = _op()
    entry = _entry(op, published=True)
    with pytest.raises(ValueError):
        request_change(
            entry=entry, proposed={"start_time": "not-a-time"}, reason="r", actor=op
        )
    # Nothing was filed, so approval has nothing to choke on later.
    assert entry.change_requests.count() == 0


def test_approve_applies_change_and_requires_different_approver() -> None:
    """Approval applies the proposed change but the requester cannot self-approve."""
    requester = _op()
    approver = _op()
    entry = _entry(requester, published=True)

    change = request_change(
        entry=entry,
        proposed={"start_time": "19:00", "note": "shifted"},
        reason="cast request",
        actor=requester,
    )
    AuditEntry.objects.get(action=AuditAction.SCHEDULE_CHANGE_REQUESTED.value)

    # Separation of duties: the requester cannot approve their own change.
    with pytest.raises(ValueError):
        approve_change(request=change, actor=requester)
    entry.refresh_from_db()
    assert entry.start_time == time(18, 0)  # unchanged until approved

    approve_change(request=change, actor=approver, decision_note="ok")
    change.refresh_from_db()
    entry.refresh_from_db()
    assert change.status == ChangeRequestStatus.APPROVED.value
    assert change.decided_by_id == approver.pk
    assert entry.start_time == time(19, 0)
    assert entry.note == "shifted"
    AuditEntry.objects.get(action=AuditAction.SCHEDULE_CHANGE_APPROVED.value)


def test_reject_change_leaves_entry_untouched() -> None:
    """Rejecting a change does not modify the entry."""
    requester = _op()
    approver = _op()
    entry = _entry(requester, published=True)
    change = request_change(
        entry=entry, proposed={"note": "no"}, reason="r", actor=requester
    )

    reject_change(request=change, actor=approver, decision_note="not now")
    change.refresh_from_db()
    entry.refresh_from_db()
    assert change.status == ChangeRequestStatus.REJECTED.value
    assert entry.note == ""
    AuditEntry.objects.get(action=AuditAction.SCHEDULE_CHANGE_REJECTED.value)


def test_unpublish_hides_without_delete() -> None:
    """Unpublish flips status to unpublished; the row still exists."""
    op = _op()
    entry = _entry(op, published=True)
    unpublish_entry(entry, actor=op, reason="typo")
    assert entry.status == ScheduleStatus.UNPUBLISHED.value
    assert ScheduleEntry.objects.filter(id=entry.id).exists()
    AuditEntry.objects.get(action=AuditAction.SCHEDULE_UNPUBLISHED.value)


def test_double_approve_rejected() -> None:
    """A non-pending change request cannot be approved again."""
    requester = _op()
    approver = _op()
    entry = _entry(requester, published=True)
    change = request_change(
        entry=entry, proposed={"note": "x"}, reason="r", actor=requester
    )
    approve_change(request=change, actor=approver)
    with pytest.raises(ValueError):
        approve_change(request=change, actor=approver)


def test_double_reject_rejected() -> None:
    """A non-pending change request cannot be rejected again."""
    requester = _op()
    approver = _op()
    entry = _entry(requester, published=True)
    change = request_change(
        entry=entry, proposed={"note": "x"}, reason="r", actor=requester
    )
    reject_change(request=change, actor=approver)
    with pytest.raises(ValueError):
        reject_change(request=change, actor=approver)
