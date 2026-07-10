"""Role-based access control: the role hierarchy and route-level guards.

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26) — this is authorization logic.

Roles form a staff privilege ladder (operator < manager < admin); fan/cast/system
sit outside it. Route guards (``RoleRequired``) plug into Ninja's ``auth=`` slot
to deny a request whose authenticated account lacks the minimum role. Field-level
redaction (see :mod:`apps.admin_rbac.redaction`) is a separate concern applied to
*response bodies*; this module governs whether the route runs at all.

The canonical rule this encodes (Technical Architecture L427-429): an operator may
see the safety-report *list*, but high/critical *detail* requires manager or above.
"""

from __future__ import annotations

from typing import cast

from django.http import HttpRequest
from ninja.security import HttpBearer

from apps.identity.auth import AuthedHttpRequest
from apps.identity.models import Account, Role
from apps.identity.services import TokenError, verify_access_token

# Staff privilege ordering. A higher number satisfies any requirement at or below
# it; non-staff roles are intentionally absent (rank 0) so they never satisfy a
# staff-role guard.
_STAFF_RANK: dict[str, int] = {
    Role.OPERATOR.value: 1,
    Role.MANAGER.value: 2,
    Role.ADMIN.value: 3,
}


def role_rank(role: str) -> int:
    """Return the privilege rank of a role (0 for non-staff/unknown)."""
    return _STAFF_RANK.get(role, 0)


def has_min_role(account: Account, *, minimum: str) -> bool:
    """Return whether ``account`` meets the ``minimum`` staff role.

    Uses the rank ladder so ``manager`` satisfies an ``operator`` requirement but
    not the reverse. ``minimum`` must itself be a staff role.
    """
    required = _STAFF_RANK.get(minimum)
    if required is None:
        raise ValueError(f"'{minimum}' is not a staff role.")
    return role_rank(account.role) >= required


class RoleRequired(HttpBearer):
    """Ninja auth class that authenticates *and* enforces a minimum staff role.

    Composes token verification with the role check so a single ``auth=`` entry
    both authenticates the caller and authorises the route. Returns the account
    when allowed (Ninja treats truthy as authorised) and ``None`` (→ 401/403)
    otherwise.
    """

    def __init__(self, minimum: str) -> None:
        """Bind the guard to the minimum role required for the route."""
        super().__init__()
        if minimum not in _STAFF_RANK:
            raise ValueError(f"'{minimum}' is not a staff role.")
        self.minimum = minimum

    def authenticate(self, request: HttpRequest, token: str) -> Account | None:
        """Return the account if the token is valid and meets the role floor."""
        try:
            account = verify_access_token(token)
        except TokenError:
            return None
        if not has_min_role(account, minimum=self.minimum):
            return None
        cast(AuthedHttpRequest, request).account = account
        return account


# Convenience guards for the common floors, so endpoints read declaratively.
operator_required = RoleRequired(Role.OPERATOR.value)
manager_required = RoleRequired(Role.MANAGER.value)
admin_required = RoleRequired(Role.ADMIN.value)
