"""RBAC mutation services: role changes that are always audited.

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26).

Any privilege change must leave an audit trail (ASS-91). Routing role changes
through :func:`change_role` guarantees the :class:`AuditEntry` is written in the
same call, so a permission grant can never happen silently.
"""

from __future__ import annotations

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.identity.models import Account, Role


def change_role(
    *, actor: Account, target: Account, new_role: str, reason: str = ""
) -> Account:
    """Change ``target``'s role and record an audit entry, returning the target.

    Validates the new role and writes the audit entry before returning so the
    change and its accountability record are atomic from the caller's view. The
    audit metadata captures the before/after role for review.
    """
    if new_role not in Role.values:
        raise ValueError(f"Unknown role '{new_role}'.")

    previous = target.role
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
