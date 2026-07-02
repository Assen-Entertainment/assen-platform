"""Acceptance tests for the audit trail helpers.

Covers: recording a generic audited action, the export helper's mandatory
reason, and rejection of unknown action strings.
"""

from __future__ import annotations

import pytest

from apps.audit.models import AuditAction, AuditEntry
from apps.audit.services import record_audit, record_export
from apps.identity.models import Account, Role

pytestmark = pytest.mark.django_db


def _admin() -> Account:
    """Create an admin account to act as the audit actor."""
    return Account.objects.create(role=Role.ADMIN.value)


def test_record_audit_persists_entry() -> None:
    """A valid audited action is stored with actor, target, and reason."""
    admin = _admin()
    entry = record_audit(
        actor=admin,
        action=AuditAction.USER_BLOCKED.value,
        target="fan-7",
        reason="repeated harassment",
    )
    assert AuditEntry.objects.count() == 1
    assert entry.actor_id == admin.pk
    assert entry.target == "fan-7"


def test_unknown_action_rejected() -> None:
    """An unrecognised action string is rejected (keeps the trail categorised)."""
    admin = _admin()
    with pytest.raises(ValueError):
        record_audit(actor=admin, action="did_a_thing", target="x")


def test_export_requires_reason() -> None:
    """Recording an export without a reason is rejected (compliance)."""
    admin = _admin()
    with pytest.raises(ValueError):
        record_export(actor=admin, target="fan_csv_2026_06", reason="   ")


def test_export_with_reason_is_recorded() -> None:
    """A reasoned export is recorded under the data_exported action."""
    admin = _admin()
    entry = record_export(
        actor=admin,
        target="fan_csv_2026_06",
        reason="monthly finance reconciliation",
    )
    assert entry.action == AuditAction.DATA_EXPORTED.value
    assert entry.reason == "monthly finance reconciliation"
