"""Tests for the admin role-assignment guards + API (RBAC v0).

Covers the fail-closed guards in ``change_role`` (admin-only + active, assignable
roles, required reason, last-active-admin backstop, inactive-admin exclusion,
no-op) and the admin API (assign 200, conflicts 409, invalid role / blank reason
400/422, staff list, and the admin-only gate).
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from django.test import Client

from apps.admin_rbac.services import RoleChangeConflict, change_role
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

ROLES = "/api/admin/rbac/roles"
JSON = "application/json"
WHY = "org change"  # a non-blank reason for the happy paths


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


# --------------------------------------------------------------------------- #
# Service guards
# --------------------------------------------------------------------------- #
def test_change_role_requires_admin_actor() -> None:
    """A non-admin actor cannot change roles (defence-in-depth over the route)."""
    manager = _account(Role.MANAGER.value)
    target = _account(Role.FAN.value)
    with pytest.raises(RoleChangeConflict):
        change_role(actor=manager, target=target, new_role=Role.OPERATOR.value, reason=WHY)


def test_change_role_refuses_unassignable_and_unknown_roles() -> None:
    """cast/system are not assignable here, and an unknown role is rejected."""
    admin = _account(Role.ADMIN.value)
    target = _account(Role.FAN.value)
    with pytest.raises(ValueError):
        change_role(actor=admin, target=target, new_role=Role.CAST.value, reason=WHY)
    with pytest.raises(ValueError):
        change_role(actor=admin, target=target, new_role="wizard", reason=WHY)


def test_change_role_requires_reason() -> None:
    """A blank (or whitespace-only) reason is refused (audit completeness)."""
    admin = _account(Role.ADMIN.value)
    target = _account(Role.FAN.value)
    with pytest.raises(ValueError):
        change_role(actor=admin, target=target, new_role=Role.OPERATOR.value, reason="")
    with pytest.raises(ValueError):
        change_role(actor=admin, target=target, new_role=Role.OPERATOR.value, reason="   ")


def test_change_role_refuses_noop() -> None:
    """Assigning the role the account already has is refused."""
    admin = _account(Role.ADMIN.value)
    target = _account(Role.OPERATOR.value)
    with pytest.raises(RoleChangeConflict):
        change_role(actor=admin, target=target, new_role=Role.OPERATOR.value, reason=WHY)


def test_cannot_remove_last_admin() -> None:
    """The sole admin cannot be demoted to zero admins (org-lockout backstop)."""
    admin = _account(Role.ADMIN.value)  # the only admin
    with pytest.raises(RoleChangeConflict):
        change_role(actor=admin, target=admin, new_role=Role.OPERATOR.value, reason=WHY)
    admin.refresh_from_db()
    assert admin.role == Role.ADMIN.value  # unchanged


def test_admin_step_down_allowed_when_another_admin_remains() -> None:
    """An admin may step down (self-demote) while another admin still exists."""
    admin = _account(Role.ADMIN.value)
    _account(Role.ADMIN.value)  # a second admin remains
    updated = change_role(actor=admin, target=admin, new_role=Role.MANAGER.value, reason=WHY)
    assert updated.role == Role.MANAGER.value


def test_demote_admin_allowed_when_another_admin_remains() -> None:
    """Demoting another admin is allowed while an admin still remains."""
    actor = _account(Role.ADMIN.value)
    other = _account(Role.ADMIN.value)
    updated = change_role(actor=actor, target=other, new_role=Role.MANAGER.value, reason=WHY)
    assert updated.role == Role.MANAGER.value


def test_inactive_admins_do_not_count_as_survivors() -> None:
    """An inactive admin row does not keep the sole active admin from being last."""
    admin = _account(Role.ADMIN.value)  # the only ACTIVE admin
    Account.objects.create(role=Role.ADMIN.value, is_active=False)  # inactive admin
    with pytest.raises(RoleChangeConflict):
        change_role(actor=admin, target=admin, new_role=Role.OPERATOR.value, reason=WHY)
    admin.refresh_from_db()
    assert admin.role == Role.ADMIN.value


def test_inactive_actor_cannot_change_roles() -> None:
    """A deactivated admin actor is refused (authz re-checked on the locked row)."""
    actor = _account(Role.ADMIN.value)
    actor.is_active = False
    actor.save(update_fields=["is_active"])
    _account(Role.ADMIN.value)  # another active admin exists
    target = _account(Role.FAN.value)
    with pytest.raises(RoleChangeConflict):
        change_role(actor=actor, target=target, new_role=Role.OPERATOR.value, reason=WHY)


def test_promote_fan_to_admin_records_stripped_reason() -> None:
    """An admin can promote a fan to admin; the audit reason is stored stripped."""
    from apps.audit.models import AuditAction, AuditEntry

    admin = _account(Role.ADMIN.value)
    target = _account(Role.FAN.value)
    updated = change_role(
        actor=admin, target=target, new_role=Role.ADMIN.value, reason="  hand off  "
    )
    assert updated.role == Role.ADMIN.value
    entry = AuditEntry.objects.get(action=AuditAction.ROLE_CHANGED.value, target=str(target.fan_id))
    assert entry.reason == "hand off"


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
def _assign(client: Client, admin: Account, target: Account, role: str, **over: object) -> Any:
    """POST a role assignment and return the response."""
    data: dict[str, object] = {"account_id": str(target.fan_id), "role": role, "reason": WHY}
    data.update(over)
    return client.post(ROLES, data=json.dumps(data), content_type=JSON, headers=_auth(admin))


def test_admin_assigns_role_via_api(client: Client) -> None:
    """An admin promotes a fan to operator via the API."""
    admin = _account(Role.ADMIN.value)
    target = _account(Role.FAN.value)
    res = _assign(client, admin, target, Role.OPERATOR.value, reason="floor staff")
    assert res.status_code == 200
    assert res.json()["role"] == "operator"
    target.refresh_from_db()
    assert target.role == Role.OPERATOR.value


def test_api_conflicts_are_409(client: Client) -> None:
    """Last-admin demotion and a no-op return 409 (conflict)."""
    admin = _account(Role.ADMIN.value)  # sole admin
    assert _assign(client, admin, admin, Role.MANAGER.value).status_code == 409
    op = _account(Role.OPERATOR.value)
    assert _assign(client, admin, op, Role.OPERATOR.value).status_code == 409


def test_api_invalid_role_is_400(client: Client) -> None:
    """An unknown or non-assignable role returns 400."""
    admin = _account(Role.ADMIN.value)
    target = _account(Role.FAN.value)
    assert _assign(client, admin, target, "wizard").status_code == 400
    assert _assign(client, admin, target, Role.CAST.value).status_code == 400


def test_api_blank_reason_is_422(client: Client) -> None:
    """A missing/blank reason is rejected by request validation (422)."""
    admin = _account(Role.ADMIN.value)
    target = _account(Role.FAN.value)
    res = client.post(
        ROLES,
        data=json.dumps({"account_id": str(target.fan_id), "role": Role.OPERATOR.value}),
        content_type=JSON,
        headers=_auth(admin),
    )
    assert res.status_code == 422


def test_api_unknown_account_is_404(client: Client) -> None:
    """Assigning to a non-existent account id is a 404."""
    admin = _account(Role.ADMIN.value)
    res = client.post(
        ROLES,
        data=json.dumps(
            {"account_id": str(uuid.uuid4()), "role": Role.OPERATOR.value, "reason": WHY}
        ),
        content_type=JSON,
        headers=_auth(admin),
    )
    assert res.status_code == 404


def test_api_lists_staff(client: Client) -> None:
    """The staff list returns operator/manager/admin accounts, not fans."""
    admin = _account(Role.ADMIN.value)
    _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    res = client.get(ROLES, headers=_auth(admin))
    assert res.status_code == 200
    ids = {row["account_id"] for row in res.json()}
    assert str(fan.fan_id) not in ids
    assert str(admin.fan_id) in ids


def test_non_admin_cannot_reach_rbac(client: Client) -> None:
    """Manager/operator/fan and anonymous are refused on the RBAC surface."""
    manager = _account(Role.MANAGER.value)
    operator = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    assert client.get(ROLES, headers=_auth(manager)).status_code in {401, 403}
    assert client.get(ROLES, headers=_auth(operator)).status_code in {401, 403}
    assert client.get(ROLES, headers=_auth(fan)).status_code in {401, 403}
    assert client.get(ROLES).status_code in {401, 403}
