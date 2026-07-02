"""Field-level redaction for safety data by role (Technical Architecture L427).

The route guard decides *whether* an endpoint runs; redaction decides *which
fields* of the response a given role may see. The load-bearing rule: an operator
may list safety reports (id, type, severity, status) but the detail fields of a
``manager_only`` (high/critical) report are withheld unless the viewer is manager
or above. Encoding this as a response transform keeps the policy in one place
rather than scattered across serializers.
"""

from __future__ import annotations

from typing import Any

from apps.admin_rbac.permissions import has_min_role
from apps.identity.models import Account, Role

# Summary fields any staff member (operator+) may see for a safety report.
SAFETY_SUMMARY_FIELDS: frozenset[str] = frozenset(
    {
        "safety_report_id",
        "report_type",
        "severity",
        "status",
        "visibility",
        "created_at",
    }
)

# Detail fields restricted to manager+. ``detail_ref`` points at the restricted
# store; even the reference is manager-gated so operators cannot fetch it.
SAFETY_DETAIL_FIELDS: frozenset[str] = frozenset(
    {
        "detail_ref",
        "reporter_id",
        "target_id",
        "resolution_note",
        "manager_note",
    }
)

# Sentinel placed in place of a withheld value so the response shape is stable
# (clients see the key exists but is redacted) rather than the key vanishing.
REDACTED = "[redacted]"


def can_view_safety_detail(account: Account) -> bool:
    """Return whether the account may see manager_only safety detail (manager+)."""
    return has_min_role(account, minimum=Role.MANAGER.value)


def redact_safety_report(report: dict[str, Any], *, viewer: Account) -> dict[str, Any]:
    """Return a copy of ``report`` with detail fields redacted for non-managers.

    Operators keep the summary fields and get ``REDACTED`` for detail fields of a
    ``manager_only`` report. For a ``restricted`` (non-sensitive) report there is
    nothing extra to hide beyond the detail set, which still requires manager+.
    Managers and admins see everything. The input is never mutated.
    """
    if can_view_safety_detail(viewer):
        return dict(report)

    visible: dict[str, Any] = {}
    for key, value in report.items():
        if key in SAFETY_DETAIL_FIELDS:
            visible[key] = REDACTED
        else:
            visible[key] = value
    return visible


def redact_safety_report_list(
    reports: list[dict[str, Any]], *, viewer: Account
) -> list[dict[str, Any]]:
    """Redact each report in a list according to the viewer's role.

    Listing is allowed for operators (the route guard permits it); this ensures
    each row in that list is still field-redacted.
    """
    return [redact_safety_report(report, viewer=viewer) for report in reports]
