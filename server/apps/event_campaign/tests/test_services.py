"""Tests for the event-campaign service (F10, ASS-107 v0).

Covers the operator lifecycle (create/update/publish/unpublish/close), the fan
reserve/cancel/view flows, the guards (non-fan, blocked fan, non-published,
duplicate hold, terminal states), and the canonical ``event_reserved`` /
``event_reservation_cancelled`` / ``event_viewed`` emission. Price values and
external/seat/prepaid ticketing are out of v0 and not exercised here.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEntry
from apps.event_campaign.models import (
    CampaignStatus,
    EventCampaign,
    EventReservation,
    EventReservationStatus,
    EventType,
)
from apps.event_campaign.services import (
    cancel_event_reservation,
    close_campaign,
    create_campaign,
    publish_campaign,
    record_event_view,
    reserve_event,
    unpublish_campaign,
    update_campaign,
)
from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account, Role
from apps.safety.models import BlockScope, UserBlock

pytestmark = pytest.mark.django_db


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _operator() -> Account:
    """Create an operator account (the campaign author)."""
    return _account(Role.OPERATOR.value)


def _fan() -> Account:
    """Create a fan account."""
    return _account(Role.FAN.value)


def _draft(operator: Account) -> EventCampaign:
    """Create a draft campaign starting in the near future."""
    return create_campaign(
        actor=operator,
        title="Birthday Live",
        starts_at=timezone.now() + timedelta(days=7),
        event_type=EventType.BIRTHDAY.value,
    )


def _published(operator: Account) -> EventCampaign:
    """Create and publish a campaign."""
    campaign = _draft(operator)
    return publish_campaign(campaign=campaign, actor=operator)


def _block(fan: Account, actor: Account, scope: str) -> UserBlock:
    """Place an active hard block on a fan."""
    return UserBlock.objects.create(
        target=fan,
        block_scope=scope,
        block_reason="policy_violation",
        effective_from=timezone.now(),
        created_by=actor,
    )


def test_create_campaign_is_draft_and_audited() -> None:
    """A new campaign starts as a draft (fan-invisible) with an audit entry."""
    operator = _operator()
    campaign = _draft(operator)
    assert campaign.status == CampaignStatus.DRAFT.value
    assert campaign.created_by_id == operator.id
    assert AuditEntry.objects.filter(
        action=AuditAction.EVENT_CAMPAIGN_CREATED.value, target=str(campaign.id)
    ).exists()


def test_create_requires_title_and_valid_window() -> None:
    """Title is required and ends_at cannot precede starts_at."""
    operator = _operator()
    with pytest.raises(ValueError, match="title"):
        create_campaign(actor=operator, title="  ", starts_at=timezone.now() + timedelta(days=1))
    with pytest.raises(ValueError, match="ends_at"):
        create_campaign(
            actor=operator,
            title="x",
            starts_at=timezone.now() + timedelta(days=2),
            ends_at=timezone.now() + timedelta(days=1),
        )


def test_unknown_event_type_rejected() -> None:
    """An out-of-domain event_type is rejected."""
    operator = _operator()
    with pytest.raises(ValueError, match="event_type"):
        create_campaign(
            actor=operator,
            title="x",
            starts_at=timezone.now() + timedelta(days=1),
            event_type="rave",
        )


def test_publish_unpublish_close_lifecycle() -> None:
    """Draft publishes, unpublishes back to draft, and closes (terminal)."""
    operator = _operator()
    campaign = _draft(operator)
    published = publish_campaign(campaign=campaign, actor=operator)
    assert published.status == CampaignStatus.PUBLISHED.value
    drafted = unpublish_campaign(campaign=published, actor=operator)
    assert drafted.status == CampaignStatus.DRAFT.value
    published_again = publish_campaign(campaign=drafted, actor=operator)
    closed = close_campaign(campaign=published_again, actor=operator)
    assert closed.status == CampaignStatus.CLOSED.value
    with pytest.raises(ValueError, match="already closed"):
        close_campaign(campaign=closed, actor=operator)


def test_publish_non_draft_rejected() -> None:
    """Publishing a non-draft campaign is rejected."""
    operator = _operator()
    published = _published(operator)
    with pytest.raises(ValueError, match="publish"):
        publish_campaign(campaign=published, actor=operator)


def test_update_requires_draft() -> None:
    """A draft is editable; a published/closed campaign is not (publish = the gate)."""
    operator = _operator()
    campaign = _draft(operator)
    updated = update_campaign(campaign=campaign, actor=operator, title="New Title")
    assert updated.title == "New Title"
    entry = AuditEntry.objects.get(
        action=AuditAction.EVENT_CAMPAIGN_UPDATED.value, target=str(campaign.id)
    )
    assert entry.metadata["changed"] == ["title"]
    # A published campaign cannot be edited in place — that would bypass the
    # publish-as-approval gate. It must be unpublished first.
    published = publish_campaign(campaign=updated, actor=operator)
    with pytest.raises(ValueError, match="draft"):
        update_campaign(campaign=published, actor=operator, title="Live Edit")
    # Closed is likewise not editable.
    closed = close_campaign(campaign=_draft(operator), actor=operator)
    with pytest.raises(ValueError, match="draft"):
        update_campaign(campaign=closed, actor=operator, title="Nope")


def test_reserve_emits_event_reserved() -> None:
    """A fan reserves a published campaign: row + event_reserved with full payload."""
    operator = _operator()
    fan = _fan()
    campaign = _published(operator)
    reservation = reserve_event(campaign=campaign, fan=fan, actor=fan)
    assert reservation.status == EventReservationStatus.RESERVED.value

    event = EventRecord.objects.get(event_name=EventName.EVENT_RESERVED.value)
    assert event.payload["fan_id"] == str(fan.fan_id)
    assert event.payload["event_campaign_id"] == str(campaign.id)
    assert event.payload["reservation_id"] == str(reservation.id)
    assert event.payload["event_type"] == EventType.BIRTHDAY.value
    assert event.payload["reservation_status"] == EventReservationStatus.RESERVED.value
    assert event.ids["event_campaign_id"] == str(campaign.id)


def test_reserve_waitlisted_status() -> None:
    """A fan can waitlist; the status flows into the event payload."""
    operator = _operator()
    fan = _fan()
    campaign = _published(operator)
    reservation = reserve_event(
        campaign=campaign, fan=fan, actor=fan, status=EventReservationStatus.WAITLISTED.value
    )
    assert reservation.status == EventReservationStatus.WAITLISTED.value
    event = EventRecord.objects.get(event_name=EventName.EVENT_RESERVED.value)
    assert event.payload["reservation_status"] == "waitlisted"


def test_reserve_requires_published_campaign() -> None:
    """A draft campaign cannot be reserved."""
    operator = _operator()
    fan = _fan()
    draft = _draft(operator)
    with pytest.raises(ValueError, match="published"):
        reserve_event(campaign=draft, fan=fan, actor=fan)


def test_reserve_rejects_non_fan_subject() -> None:
    """Only fan accounts can hold an event reservation."""
    operator = _operator()
    campaign = _published(operator)
    with pytest.raises(ValueError, match="fan accounts"):
        reserve_event(campaign=campaign, fan=operator, actor=operator)


def test_blocked_fan_cannot_reserve() -> None:
    """A fandom-feature (or reservation) block bars reserving an event."""
    operator = _operator()
    fan = _fan()
    campaign = _published(operator)
    _block(fan, operator, BlockScope.FANDOM_FEATURE.value)
    with pytest.raises(ValueError, match="blocked"):
        reserve_event(campaign=campaign, fan=fan, actor=fan)
    assert not EventReservation.objects.exists()


def test_duplicate_active_reservation_rejected() -> None:
    """A second active hold on the same campaign by the same fan is refused."""
    operator = _operator()
    fan = _fan()
    campaign = _published(operator)
    reserve_event(campaign=campaign, fan=fan, actor=fan)
    with pytest.raises(ValueError, match="already exists"):
        reserve_event(campaign=campaign, fan=fan, actor=fan)


def test_cancel_emits_event_reservation_cancelled_and_allows_rereserve() -> None:
    """Cancelling emits the corrective event and frees the fan to re-reserve."""
    operator = _operator()
    fan = _fan()
    campaign = _published(operator)
    reservation = reserve_event(campaign=campaign, fan=fan, actor=fan)
    cancelled = cancel_event_reservation(reservation=reservation, actor=fan)
    assert cancelled.status == EventReservationStatus.CANCELLED.value
    assert EventRecord.objects.filter(
        event_name=EventName.EVENT_RESERVATION_CANCELLED.value
    ).exists()
    with pytest.raises(ValueError, match="cancel"):
        cancel_event_reservation(reservation=cancelled, actor=fan)
    # Re-reserving the same campaign is now allowed.
    again = reserve_event(campaign=campaign, fan=fan, actor=fan)
    assert again.status == EventReservationStatus.RESERVED.value


def test_record_view_emits_event_viewed() -> None:
    """A fan impression of a published campaign emits event_viewed."""
    operator = _operator()
    fan = _fan()
    campaign = _published(operator)
    record_event_view(campaign=campaign, fan=fan)
    event = EventRecord.objects.get(event_name=EventName.EVENT_VIEWED.value)
    assert event.payload["event_campaign_id"] == str(campaign.id)


def test_record_view_requires_published() -> None:
    """A draft campaign cannot record an impression."""
    operator = _operator()
    fan = _fan()
    draft = _draft(operator)
    with pytest.raises(ValueError, match="published"):
        record_event_view(campaign=draft, fan=fan)
