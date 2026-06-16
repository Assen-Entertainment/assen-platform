"""RBAC mutation services: role changes that are always audited.

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26).

Any privilege change must leave an audit trail (ASS-91). Routing role changes
through :func:`change_role` guarantees the :class:`AuditEntry` is written in the
same call, so a permission grant can never happen silently. The change is
fail-closed: it locks the target, refuses to assign a non-staff-manageable role,
and protects against the two lockout footguns — an admin demoting themselves and
removing the last admin.
"""

from __future__ import annotations

from django.db import transaction

from apps.admin_rbac.permissions import has_min_role
from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.identity.models import Account, Role

# Roles an admin may assign/revoke through this RBAC surface: the staff ladder
# plus a revoke-to-fan. ``cast`` and ``system`` are managed elsewhere (cast
# onboarding / jobs), so they are not assignable here (fail-closed).
ASSIGNABLE_ROLES: frozenset[str] = frozenset(
    {Role.FAN.value, Role.OPERATOR.value, Role.MANAGER.value, Role.ADMIN.value}
)


class RoleChangeConflict(ValueError):
    """A role change is refused by a safety guard (last-admin / self / no-op)."""


@transaction.atomic
def change_role(*, actor: Account, target: Account, new_role: str, reason: str = "") -> Account:
    """Change ``target``'s role and record an audit entry, returning the target.

    Fail-closed guards (all raise before any write):
      - the actor must be an **active admin**, re-checked on the locked actor row
        inside the transaction (the in-memory actor may be stale);
      - ``new_role`` must be a known, assignable role (not cast/system);
      - the last **active** admin cannot be demoted to zero (org-lockout backstop;
        also blocks a sole admin self-demoting). Inactive admins do not count as
        survivors;
      - a no-op (same role) is refused.

    The target row is locked for the duration so the last-admin count and the
    transition cannot race a concurrent change. The audit metadata captures the
    before/after role for review.
    """
    if new_role not in Role.values:
        raise ValueError(f"Unknown role '{new_role}'.")
    if new_role not in ASSIGNABLE_ROLES:
        raise ValueError("That role cannot be assigned through RBAC.")
    # A role change must record *why* — the audit trail is the accountability
    # record for an authz mutation, so a blank reason is refused.
    reason = reason.strip()
    if not reason:
        raise ValueError("A reason is required for a role change.")

    # Re-load + lock the actor inside the transaction and re-check authz against
    # committed state: the in-memory ``actor`` can be stale (concurrently demoted
    # or deactivated between authentication and here), so authorise on the locked
    # row, requiring an active admin.
    actor = Account.objects.select_for_update().get(pk=actor.pk)
    if not (actor.is_active and has_min_role(actor, minimum=Role.ADMIN.value)):
        raise RoleChangeConflict("Only an active admin can change roles.")

    # Lock the target so its own transition is race-free.
    target = Account.objects.select_for_update().get(pk=target.pk)
    previous = target.role
    if previous == new_role:
        raise RoleChangeConflict("Account already has that role.")

    # Lockout backstop: a demotion must never drop the admin count to zero.
    # The invariant ("at least one admin remains") spans multiple rows, so the
    # single target lock is not enough: two transactions demoting two distinct
    # admins concurrently would each see the other as the survivor (write-skew →
    # zero admins). We therefore **lock the surviving-admin rows** (not just count
    # them); a concurrent cross-demotion must also lock this set, so the two
    # serialise (one waits / deadlock-aborts) and can never both pass. Materialise
    # with list() so the FOR UPDATE row locks are actually taken.
    if previous == Role.ADMIN.value and new_role != Role.ADMIN.value:
        surviving_admins = list(
            Account.objects.select_for_update()
            .filter(role=Role.ADMIN.value, is_active=True)
            .exclude(pk=target.pk)
            .values_list("pk", flat=True)
        )
        if not surviving_admins:
            raise RoleChangeConflict("Cannot remove the last active admin.")

    target.role = new_role
    target.save(update_fields=["role"])
    record_audit(
        actor=actor,
        action=AuditAction.ROLE_CHANGED.value,
        target=str(target.fan_id),
        reason=reason,
        metadata={"from": previous, "to": new_role},
    )
    return target
