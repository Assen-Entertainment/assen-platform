"""Helpers for recording audit entries.

A thin, typed funnel so privileged code paths record audit entries the same way,
and so ``reason`` is required where compliance demands it (exports, safety
detail access) rather than being an afterthought.
"""

from __future__ import annotations

from typing import Any

from apps.audit.models import AuditAction, AuditEntry
from apps.identity.models import Account


def record_audit(
    *,
    actor: Account,
    action: str,
    target: str,
    reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> AuditEntry:
    """Persist one audit entry, returning it.

    Validates ``action`` against the enum so a typo cannot silently create an
    uncategorisable entry.
    """
    if action not in AuditAction.values:
        raise ValueError(f"Unknown audit action '{action}'.")
    return AuditEntry.objects.create(
        actor=actor,
        action=action,
        target=target,
        reason=reason,
        metadata=metadata or {},
    )


def record_export(
    *, actor: Account, target: str, reason: str, metadata: dict[str, Any] | None = None
) -> AuditEntry:
    """Record a data export with a mandatory reason (compliance).

    Exports without a stated reason are rejected so the trail can answer "why was
    this data taken out" during review.
    """
    if not reason.strip():
        raise ValueError("Data export audit requires a non-empty reason.")
    return record_audit(
        actor=actor,
        action=AuditAction.DATA_EXPORTED.value,
        target=target,
        reason=reason,
        metadata=metadata,
    )
