"""Consent recording service.

Recording a consent is two coupled facts: the durable :class:`ConsentRecord` the
gate reads, and the ``rule_consent_given`` event the analytics/audit layer reads.
This service writes both so they cannot drift.
"""

from __future__ import annotations

from apps.consent.models import ConsentKind, ConsentRecord
from apps.identity.models import Account


def record_consent(
    *, account: Account, kind: str, version: str
) -> ConsentRecord:
    """Persist a consent grant and emit the corresponding event.

    Validates ``kind`` against the enum. For the ``rule`` kind it also emits a
    ``rule_consent_given`` event (P0_required) so the consent shows up in the
    event log used for safety/audit baselining.
    """
    if kind not in ConsentKind.values:
        raise ValueError(f"Unknown consent kind '{kind}'.")

    record = ConsentRecord.objects.create(
        account=account, kind=kind, version=version
    )

    if kind == ConsentKind.RULE.value:
        # Imported lazily to avoid a hard import cycle consent <-> event_log.
        from django.utils import timezone

        from apps.event_log.events import ActorType, EventName, EventSource
        from apps.event_log.services import emit_event

        emit_event(
            event_name=EventName.RULE_CONSENT_GIVEN.value,
            occurred_at=timezone.now(),
            actor_type=ActorType.FAN.value,
            source=EventSource.WEB.value,
            fan_id=str(account.fan_id),
            payload={
                "fan_id": str(account.fan_id),
                "consent_kind": kind,
                "consent_version": version,
            },
        )

    return record
