"""Admin RBAC API: assign/revoke staff roles (ASS RBAC v0).

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26) — this surface changes who can do
what. **Merge is gated on explicit #26 human approval** even after AI review.

``admin_required`` so only an admin may reach it. Role changes go through
:func:`apps.admin_rbac.services.change_role`, which audits every change and
fail-closed-guards the lockout footguns (self-demotion, last admin). A safety
guard refusal is a 409 (conflict); an unknown/non-assignable role is a 400.
"""

from __future__ import annotations

import uuid

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import admin_required
from apps.admin_rbac.services import RoleChangeConflict, change_role
from apps.identity.auth import authed
from apps.identity.models import Account, Role
from config.api import api

admin_router = Router(auth=admin_required, tags=["admin-rbac"])

_STAFF_ROLES = (Role.OPERATOR.value, Role.MANAGER.value, Role.ADMIN.value)


class RbacError(Schema):
    """Stable error shape for RBAC endpoints."""

    detail: str


class AccountRoleOut(Schema):
    """An account id + its current role."""

    account_id: uuid.UUID
    role: str


class RoleAssignIn(Schema):
    """Admin payload to set an account's role."""

    account_id: uuid.UUID
    role: str
    reason: str = Field(min_length=1, max_length=512)


@admin_router.post(
    "/roles",
    response={200: AccountRoleOut, 400: RbacError, 404: RbacError, 409: RbacError},
)
def assign_role(
    request: HttpRequest, payload: RoleAssignIn
) -> tuple[int, AccountRoleOut | RbacError]:
    """Assign or revoke an account's staff role (admin only, audited)."""
    target = get_object_or_404(Account, fan_id=payload.account_id)
    try:
        updated = change_role(
            actor=_actor(request),
            target=target,
            new_role=payload.role,
            reason=payload.reason,
        )
    except RoleChangeConflict as exc:
        return 409, RbacError(detail=str(exc))
    except ValueError as exc:
        return 400, RbacError(detail=str(exc))
    return 200, AccountRoleOut(account_id=updated.fan_id, role=updated.role)


@admin_router.get("/roles", response=list[AccountRoleOut])
def list_staff(request: HttpRequest) -> list[AccountRoleOut]:
    """List staff accounts and their roles (operator / manager / admin)."""
    del request
    rows = Account.objects.filter(role__in=_STAFF_ROLES)
    return [AccountRoleOut(account_id=a.fan_id, role=a.role) for a in rows]


def _actor(request: HttpRequest) -> Account:
    """Return the authenticated admin account supplied by the auth class."""
    # request.auth is untyped without Ninja stubs (same idiom as visit/api.py).
    return authed(request)


api.add_router("/admin/rbac", admin_router)
