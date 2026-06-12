"""Acceptance tests for RBAC route guards and field-level redaction.

Covers ASS-91: the six roles, route-level minimum-role enforcement, and the
operator-vs-manager safety-detail redaction rule (operator sees the list, detail
is manager+). Also covers that role changes are audited.
"""

from __future__ import annotations

import pytest
from django.http import HttpRequest

from apps.admin_rbac.permissions import (
    RoleRequired,
    has_min_role,
    role_rank,
)
from apps.admin_rbac.redaction import (
    REDACTED,
    can_view_safety_detail,
    redact_safety_report,
    redact_safety_report_list,
)
from apps.admin_rbac.services import change_role
from apps.audit.models import AuditAction, AuditEntry
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db


def _account(role: str, *, username: str = "") -> Account:
    """Create an account with the given role."""
    return Account.objects.create(role=role, username=username)


# --------------------------------------------------------------------------
# Role ladder + route guard
# --------------------------------------------------------------------------


def test_six_roles_exist() -> None:
    """The role enum defines exactly the six platform roles."""
    assert set(Role.values) == {
        "fan",
        "cast",
        "operator",
        "manager",
        "admin",
        "system",
    }


def test_role_ladder_ordering() -> None:
    """Staff ranks increase operator < manager < admin; non-staff are rank 0."""
    assert role_rank(Role.OPERATOR.value) < role_rank(Role.MANAGER.value)
    assert role_rank(Role.MANAGER.value) < role_rank(Role.ADMIN.value)
    assert role_rank(Role.FAN.value) == 0
    assert role_rank(Role.SYSTEM.value) == 0


def test_has_min_role_is_inclusive_upward() -> None:
    """A manager satisfies an operator floor; an operator does not satisfy manager."""
    manager = _account(Role.MANAGER.value)
    operator = _account(Role.OPERATOR.value)
    assert has_min_role(manager, minimum=Role.OPERATOR.value) is True
    assert has_min_role(operator, minimum=Role.MANAGER.value) is False


def test_route_guard_allows_sufficient_role_and_denies_insufficient() -> None:
    """RoleRequired authenticates the token and enforces the minimum role."""
    guard = RoleRequired(Role.MANAGER.value)

    manager = _account(Role.MANAGER.value)
    operator = _account(Role.OPERATOR.value)
    manager_token = issue_token_pair(manager).access_token
    operator_token = issue_token_pair(operator).access_token

    # Manager passes (returns the account), operator is denied (None).
    assert guard.authenticate(HttpRequest(), manager_token) is not None
    assert guard.authenticate(HttpRequest(), operator_token) is None
    # A bogus token is denied regardless of role.
    assert guard.authenticate(HttpRequest(), "garbage") is None


# --------------------------------------------------------------------------
# Field-level redaction
# --------------------------------------------------------------------------


def _safety_report() -> dict[str, object]:
    """A manager_only safety report with both summary and detail fields."""
    return {
        "safety_report_id": "sr-1",
        "report_type": "verbal_abuse",
        "severity": "high",
        "status": "pending",
        "visibility": "manager_only",
        "created_at": "2026-06-12T00:00:00Z",
        "detail_ref": "restricted-store://sr-1",
        "reporter_id": "fan-9",
        "target_id": "fan-3",
        "resolution_note": "sensitive",
    }


def test_operator_sees_summary_but_detail_is_redacted() -> None:
    """An operator gets the list/summary fields; detail fields are redacted."""
    operator = _account(Role.OPERATOR.value)
    assert can_view_safety_detail(operator) is False

    view = redact_safety_report(_safety_report(), viewer=operator)
    # Summary remains visible.
    assert view["severity"] == "high"
    assert view["report_type"] == "verbal_abuse"
    # Detail is withheld but the keys remain (stable shape).
    assert view["detail_ref"] == REDACTED
    assert view["reporter_id"] == REDACTED
    assert view["resolution_note"] == REDACTED


def test_manager_sees_full_detail() -> None:
    """A manager sees every field, including detail."""
    manager = _account(Role.MANAGER.value)
    assert can_view_safety_detail(manager) is True

    view = redact_safety_report(_safety_report(), viewer=manager)
    assert view["detail_ref"] == "restricted-store://sr-1"
    assert view["reporter_id"] == "fan-9"


def test_admin_sees_full_detail() -> None:
    """An admin (above manager) also sees detail."""
    admin = _account(Role.ADMIN.value)
    view = redact_safety_report(_safety_report(), viewer=admin)
    assert view["resolution_note"] == "sensitive"


def test_redaction_does_not_mutate_input() -> None:
    """Redaction returns a copy; the source report is untouched."""
    operator = _account(Role.OPERATOR.value)
    report = _safety_report()
    redact_safety_report(report, viewer=operator)
    assert report["detail_ref"] == "restricted-store://sr-1"


def test_list_redaction_applies_per_row() -> None:
    """Operator listing redacts detail on every row."""
    operator = _account(Role.OPERATOR.value)
    rows = redact_safety_report_list([_safety_report(), _safety_report()], viewer=operator)
    assert all(row["detail_ref"] == REDACTED for row in rows)
    assert all(row["severity"] == "high" for row in rows)


# --------------------------------------------------------------------------
# Role change auditing
# --------------------------------------------------------------------------


def test_role_change_is_audited() -> None:
    """Changing a role writes an audit entry capturing from/to."""
    admin = _account(Role.ADMIN.value)
    target = _account(Role.FAN.value)

    change_role(
        actor=admin,
        target=target,
        new_role=Role.OPERATOR.value,
        reason="promote to floor staff",
    )

    target.refresh_from_db()
    assert target.role == Role.OPERATOR.value

    entry = AuditEntry.objects.get(action=AuditAction.ROLE_CHANGED.value)
    assert entry.actor_id == admin.pk
    assert entry.metadata == {"from": "fan", "to": "operator"}
    assert entry.reason == "promote to floor staff"
