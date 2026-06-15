"""Service layer for event campaigns + reservations (F10, ASS-107 v0).

Every mutation passes through this module so the operational row, the audit
trail, and the append-only analytics events stay coupled. Analytics events are
emitted **only** through :func:`apps.event_log.services.emit_event` (the
validated registry) — mirrors the visit/cheki/reservation domains.

Event mapping (Data_Event_Schema):

- reserve  → ``event_reserved``
- cancel   → ``event_reservation_cancelled``
- view     → ``event_viewed``
- campaign create/update/publish/unpublish/close → **audit only** (operator
  lifecycle; not analytics signals in the P0 registry).

Publication is the fail-closed "승인 전 비공개" gate: a campaign is fan-visible
only while ``status=published``. Blocked fans are refused at reserve
(``BlockScope.RESERVATION``/``FANDOM_FEATURE``). No price/money figure is stored
(the price value is the approval-gated, deferred slice).
"""

from __future__ import annotations

from datetime import datetime

from django.db import models, transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.event_campaign.models import (
    DEFAULT_STORE_ID,
    CampaignStatus,
    EventCampaign,
    EventReservation,
    EventReservationStatus,
    EventType,
)
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import emit_event
from apps.identity.models import Account, Role
from apps.safety.models import BlockScope
from apps.safety.services import has_active_block

# A fan can still cancel a reservation while it is in one of these states.
_ACTIVE_RESERVATION_STATUSES = (
    EventReservationStatus.RESERVED.value,
    EventReservationStatus.WAITLISTED.value,
)
# Scopes that bar a fan from reserving an event (F11: 예약/팬덤 기능 제한).
_RESERVE_BLOCK_SCOPES = [BlockScope.RESERVATION.value, BlockScope.FANDOM_FEATURE.value]


# --------------------------------------------------------------------------- #
# Operator: campaign lifecycle
# --------------------------------------------------------------------------- #
@transaction.atomic
def create_campaign(
    *,
    actor: Account,
    title: str,
    starts_at: datetime,
    event_type: str = EventType.OTHER.value,
    description: str = "",
    ends_at: datetime | None = None,
    notice: str = "",
    cast: Account | None = None,
    store_id: str = DEFAULT_STORE_ID,
) -> EventCampaign:
    """Create a campaign as a draft (fan-invisible until published)."""
    if not title.strip():
        raise ValueError("title is required.")
    _validate_enum(event_type, EventType, "event_type")
    if ends_at is not None and ends_at < starts_at:
        raise ValueError("ends_at must not be before starts_at.")
    campaign = EventCampaign.objects.create(
        title=title.strip(),
        description=description.strip(),
        event_type=event_type,
        cast=cast,
        store_id=store_id,
        starts_at=starts_at,
        ends_at=ends_at,
        notice=notice.strip(),
        created_by=actor,
    )
    _audit_campaign(actor, AuditAction.EVENT_CAMPAIGN_CREATED.value, campaign)
    return campaign


@transaction.atomic
def update_campaign(
    *,
    campaign: EventCampaign,
    actor: Account,
    title: str | None = None,
    description: str | None = None,
    event_type: str | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    notice: str | None = None,
) -> EventCampaign:
    """Edit a draft campaign; only supplied fields change.

    Editing is allowed only while the campaign is a draft: publishing is the
    approval gate ("승인 전 비공개"), so fan-visible content cannot be mutated in
    place (which would let unapproved price/participation text reach fans). To
    change a published campaign, unpublish it, edit, then republish.
    """
    campaign = _lock_campaign(campaign)
    if campaign.status != CampaignStatus.DRAFT.value:
        raise ValueError("Only a draft campaign can be edited; unpublish it first.")
    fields: list[str] = []
    if title is not None:
        if not title.strip():
            raise ValueError("title is required.")
        campaign.title = title.strip()
        fields.append("title")
    if description is not None:
        campaign.description = description.strip()
        fields.append("description")
    if event_type is not None:
        _validate_enum(event_type, EventType, "event_type")
        campaign.event_type = event_type
        fields.append("event_type")
    if starts_at is not None:
        campaign.starts_at = starts_at
        fields.append("starts_at")
    if ends_at is not None:
        campaign.ends_at = ends_at
        fields.append("ends_at")
    if notice is not None:
        campaign.notice = notice.strip()
        fields.append("notice")
    if not fields:
        raise ValueError("No campaign fields to update.")
    if campaign.ends_at is not None and campaign.ends_at < campaign.starts_at:
        raise ValueError("ends_at must not be before starts_at.")
    campaign.save(update_fields=[*fields, "updated_at"])
    _audit_campaign(
        actor,
        AuditAction.EVENT_CAMPAIGN_UPDATED.value,
        campaign,
        metadata={"changed": fields},
    )
    return campaign


@transaction.atomic
def publish_campaign(*, campaign: EventCampaign, actor: Account) -> EventCampaign:
    """Publish a draft campaign (the 공개 gate: now fan-visible)."""
    campaign = _lock_campaign(campaign)
    if campaign.status != CampaignStatus.DRAFT.value:
        raise ValueError(f"Cannot publish a campaign in status '{campaign.status}'.")
    campaign.status = CampaignStatus.PUBLISHED.value
    campaign.save(update_fields=["status", "updated_at"])
    _audit_campaign(actor, AuditAction.EVENT_CAMPAIGN_PUBLISHED.value, campaign)
    return campaign


@transaction.atomic
def unpublish_campaign(*, campaign: EventCampaign, actor: Account) -> EventCampaign:
    """Return a published campaign to draft (비공개)."""
    campaign = _lock_campaign(campaign)
    if campaign.status != CampaignStatus.PUBLISHED.value:
        raise ValueError(f"Cannot unpublish a campaign in status '{campaign.status}'.")
    campaign.status = CampaignStatus.DRAFT.value
    campaign.save(update_fields=["status", "updated_at"])
    _audit_campaign(actor, AuditAction.EVENT_CAMPAIGN_UNPUBLISHED.value, campaign)
    return campaign


@transaction.atomic
def close_campaign(*, campaign: EventCampaign, actor: Account) -> EventCampaign:
    """Close a campaign (마감, terminal). Re-closing is rejected."""
    campaign = _lock_campaign(campaign)
    if campaign.status == CampaignStatus.CLOSED.value:
        raise ValueError("Campaign is already closed.")
    campaign.status = CampaignStatus.CLOSED.value
    campaign.save(update_fields=["status", "updated_at"])
    _audit_campaign(actor, AuditAction.EVENT_CAMPAIGN_CLOSED.value, campaign)
    return campaign


# --------------------------------------------------------------------------- #
# Fan: reserve / cancel / view
# --------------------------------------------------------------------------- #
@transaction.atomic
def reserve_event(
    *,
    campaign: EventCampaign,
    fan: Account,
    actor: Account,
    status: str = EventReservationStatus.RESERVED.value,
) -> EventReservation:
    """Reserve or waitlist a published campaign for ``fan`` and emit event_reserved.

    Rejects a non-fan subject, a blocked fan, a non-published campaign, an invalid
    status, and a duplicate active hold (double-submit guard).
    """
    if fan.role != Role.FAN.value:
        raise ValueError("Event reservations can only be created for fan accounts.")
    if status not in _ACTIVE_RESERVATION_STATUSES:
        raise ValueError("Unknown reservation status.")
    if has_active_block(target=fan, scopes=_RESERVE_BLOCK_SCOPES):
        raise ValueError("Fan is blocked from reserving events.")
    campaign = _lock_campaign(campaign)
    if campaign.status != CampaignStatus.PUBLISHED.value:
        raise ValueError("Only a published campaign can be reserved.")
    if EventReservation.objects.filter(
        campaign=campaign,
        fan=fan,
        status__in=_ACTIVE_RESERVATION_STATUSES,
    ).exists():
        raise ValueError("An active reservation for this event already exists.")

    reservation = EventReservation.objects.create(
        campaign=campaign,
        fan=fan,
        status=status,
        created_by=actor,
    )
    _emit_event_reservation(
        reservation=reservation,
        event_name=EventName.EVENT_RESERVED.value,
        actor=actor,
        extra={"event_type": campaign.event_type, "reservation_status": status},
    )
    return reservation


@transaction.atomic
def cancel_event_reservation(*, reservation: EventReservation, actor: Account) -> EventReservation:
    """Cancel an active event reservation and emit event_reservation_cancelled."""
    reservation = _lock_reservation(reservation)
    if reservation.status not in _ACTIVE_RESERVATION_STATUSES:
        raise ValueError(f"Cannot cancel a reservation in status '{reservation.status}'.")
    reservation.status = EventReservationStatus.CANCELLED.value
    reservation.save(update_fields=["status", "updated_at"])
    _emit_event_reservation(
        reservation=reservation,
        event_name=EventName.EVENT_RESERVATION_CANCELLED.value,
        actor=actor,
    )
    return reservation


def record_event_view(*, campaign: EventCampaign, fan: Account) -> None:
    """Record a fan impression of a published campaign (event_viewed)."""
    if fan.role != Role.FAN.value:
        raise ValueError("Only fans record event impressions.")
    # Re-read the latest committed status so an impression is not recorded against
    # a campaign an operator just unpublished (narrows the check-then-emit window).
    campaign = EventCampaign.objects.get(pk=campaign.pk)
    if campaign.status != CampaignStatus.PUBLISHED.value:
        raise ValueError("Only a published campaign can be viewed.")
    emit_event(
        event_name=EventName.EVENT_VIEWED.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.FAN.value,
        source=EventSource.FAN_APP.value,
        actor_id=str(fan.fan_id),
        fan_id=str(fan.fan_id),
        actor_is_operator=False,
        ids={"event_campaign_id": str(campaign.id)},
        context={"store_id": campaign.store_id},
        payload={"event_campaign_id": str(campaign.id)},
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _lock_campaign(campaign: EventCampaign) -> EventCampaign:
    """Re-load the campaign under a row lock so concurrent transitions serialise."""
    return EventCampaign.objects.select_for_update().get(pk=campaign.pk)


def _lock_reservation(reservation: EventReservation) -> EventReservation:
    """Re-load the reservation under a row lock (serialises concurrent cancels)."""
    return EventReservation.objects.select_for_update().get(pk=reservation.pk)


def _audit_campaign(
    actor: Account,
    action: str,
    campaign: EventCampaign,
    *,
    metadata: dict[str, object] | None = None,
) -> None:
    """Write the audit entry for an operator campaign mutation."""
    entry_metadata: dict[str, object] = {
        "event_type": campaign.event_type,
        "status": campaign.status,
    }
    if metadata:
        entry_metadata.update(metadata)
    record_audit(
        actor=actor,
        action=action,
        target=str(campaign.id),
        metadata=entry_metadata,
    )


def _emit_event_reservation(
    *,
    reservation: EventReservation,
    event_name: str,
    actor: Account,
    extra: dict[str, str] | None = None,
) -> None:
    """Emit an event_reserved / event_reservation_cancelled signal (no PII)."""
    is_operator = actor.role != Role.FAN.value
    fan_id = str(reservation.fan.fan_id)
    campaign_id = str(reservation.campaign_id)
    payload: dict[str, object] = {
        "fan_id": fan_id,
        "event_campaign_id": campaign_id,
        "reservation_id": str(reservation.id),
    }
    if extra:
        payload.update(extra)
    emit_event(
        event_name=event_name,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value if is_operator else ActorType.FAN.value,
        source=EventSource.MANUAL.value if is_operator else EventSource.FAN_APP.value,
        actor_id=str(actor.fan_id),
        fan_id=fan_id,
        actor_is_operator=is_operator,
        ids={"event_campaign_id": campaign_id, "reservation_id": str(reservation.id)},
        context={"store_id": reservation.campaign.store_id},
        payload=payload,
    )


def _validate_enum(value: str, choices: type[models.TextChoices], field: str) -> None:
    """Raise ``ValueError`` if ``value`` is not a member of ``choices`` (no echo)."""
    if value not in choices.values:
        raise ValueError(f"Unknown {field}.")
