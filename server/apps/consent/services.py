"""Consent recording service.

Recording a consent is two coupled facts: the durable :class:`ConsentRecord` the
gate reads, and the ``rule_consent_given`` event the analytics/audit layer reads.
This service writes both so they cannot drift.
"""

from __future__ import annotations

from apps.consent.models import (
    ConsentKind,
    ConsentRecord,
    MarketingChannel,
    MarketingConsent,
)
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


def set_marketing_consent(
    *, account: Account, channel: str, enabled: bool
) -> MarketingConsent:
    """Set a fan's opt-in for one marketing channel (D8) and append an audit row.

    Upserts the current-state :class:`MarketingConsent` row and records a
    ``ConsentRecord`` (kind ``marketing``, version ``marketing:<channel>:<on|off>``)
    so the grant/withdraw history is durable. Validates ``channel`` against the enum.
    """
    if channel not in MarketingChannel.values:
        raise ValueError(f"Unknown marketing channel '{channel}'.")
    obj, _ = MarketingConsent.objects.update_or_create(
        account=account, channel=channel, defaults={"enabled": enabled}
    )
    record_consent(
        account=account,
        kind=ConsentKind.MARKETING.value,
        version=f"marketing:{channel}:{'on' if enabled else 'off'}",
    )
    return obj


def marketing_consent_state(account: Account) -> dict[str, bool]:
    """Return the fan's current opt-in per channel (missing row = False, fail-closed).

    The send-time gate reads this: a channel is messaged only when its value is True.
    """
    rows = {
        c.channel: c.enabled for c in account.marketing_consents.all()
    }
    return {ch.value: rows.get(ch.value, False) for ch in MarketingChannel}


def clear_marketing_consent(account: Account) -> None:
    """Disable every marketing channel for an account (called on withdrawal, D3).

    A plain state reset — no audit spam — since it runs as part of anonymisation.
    """
    account.marketing_consents.filter(enabled=True).update(enabled=False)
