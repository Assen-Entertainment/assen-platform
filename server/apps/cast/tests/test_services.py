"""Service tests for cast profiles + consent (ASS-92, F04).

The load-bearing assertions: the consent gate is fail-closed (a profile is hidden
until a manager grants the scope *and* an operator publishes it), each scope is
gated independently, severity-free profile content never reaches the
``cast_profile_viewed`` event, and every mutation is audited.
"""

from __future__ import annotations

import pytest

from apps.audit.models import AuditAction, AuditEntry
from apps.cast.models import (
    CastConsent,
    CastProfile,
    ConsentScope,
    ConsentStatus,
    ProfileVisibility,
)
from apps.cast.services import (
    CastProfileError,
    consent_map,
    create_cast_profile,
    public_profile,
    record_cast_consent,
    update_cast_profile,
    view_public_profile,
)
from apps.event_log.events import ActorType, EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account, Role

pytestmark = pytest.mark.django_db

_STAGE_NAME = "미라이"
_INTRO = "잘 부탁드립니다 — 연락처 010-1234-5678"


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _operator() -> Account:
    """Create an operator account."""
    return _account(Role.OPERATOR.value)


def _manager() -> Account:
    """Create a manager account."""
    return _account(Role.MANAGER.value)


def _fan() -> Account:
    """Create a fan account (the viewer)."""
    return _account(Role.FAN.value)


def _published_profile_with_name() -> tuple[CastProfile, Account]:
    """Return a PUBLIC profile whose stage name is granted (everything else not)."""
    operator = _operator()
    manager = _manager()
    profile = create_cast_profile(stage_name=_STAGE_NAME, intro=_INTRO, actor=operator)
    update_cast_profile(profile=profile, actor=operator, visibility=ProfileVisibility.PUBLIC.value)
    record_cast_consent(
        profile=profile,
        scope=ConsentScope.STAGE_NAME.value,
        status=ConsentStatus.GRANTED.value,
        actor=manager,
    )
    return profile, manager


def test_create_starts_private_hidden_and_audited() -> None:
    """A new profile is private with no consent, so it is fully hidden + audited."""
    operator = _operator()

    profile = create_cast_profile(stage_name=_STAGE_NAME, actor=operator)

    assert profile.visibility == ProfileVisibility.PRIVATE.value
    assert profile.created_by == operator
    assert not profile.consents.exists()
    assert public_profile(profile) is None
    AuditEntry.objects.get(action=AuditAction.CAST_PROFILE_CREATED.value)


def test_create_rejects_blank_stage_name() -> None:
    """A profile needs a name; a blank one is refused and writes no row."""
    with pytest.raises(CastProfileError):
        create_cast_profile(stage_name="   ", actor=_operator())
    assert not CastProfile.objects.exists()


def test_consent_map_defaults_every_scope_to_withheld() -> None:
    """Scopes with no row read as withheld (fail-closed), not granted."""
    profile = create_cast_profile(stage_name=_STAGE_NAME, actor=_operator())
    statuses = consent_map(profile)
    assert set(statuses) == set(ConsentScope.values)
    assert all(status == ConsentStatus.WITHHELD.value for status in statuses.values())


def test_public_profile_hidden_while_private_even_with_consent() -> None:
    """Visibility never overrides consent — a private profile is hidden."""
    operator = _operator()
    manager = _manager()
    profile = create_cast_profile(stage_name=_STAGE_NAME, actor=operator)
    record_cast_consent(
        profile=profile,
        scope=ConsentScope.STAGE_NAME.value,
        status=ConsentStatus.GRANTED.value,
        actor=manager,
    )
    # Granted but still PRIVATE → hidden.
    assert public_profile(profile) is None


def test_public_profile_hidden_when_name_withheld() -> None:
    """A public profile without name consent is still hidden (no nameless slot)."""
    operator = _operator()
    profile = create_cast_profile(stage_name=_STAGE_NAME, actor=operator)
    update_cast_profile(profile=profile, actor=operator, visibility=ProfileVisibility.PUBLIC.value)
    assert public_profile(profile) is None


def test_public_profile_gates_each_field_independently() -> None:
    """Name granted shows the name; photo/intro/schedule stay hidden until granted."""
    profile, manager = _published_profile_with_name()

    shown = public_profile(profile)
    assert shown is not None
    assert shown["stage_name"] == _STAGE_NAME
    # Photo / intro withheld → empty; schedule withheld → False.
    assert shown["intro"] == ""
    assert shown["photo_ref"] == ""
    assert shown["schedule_visible"] is False

    # Grant the remaining scopes.
    update_cast_profile(profile=profile, actor=manager, intro=_INTRO, photo_ref="key/1.jpg")
    for scope in (
        ConsentScope.PROFILE_INTRO.value,
        ConsentScope.PROFILE_PHOTO.value,
        ConsentScope.SCHEDULE.value,
    ):
        record_cast_consent(
            profile=profile,
            scope=scope,
            status=ConsentStatus.GRANTED.value,
            actor=manager,
        )

    shown = public_profile(profile)
    assert shown is not None
    assert shown["intro"] == _INTRO
    assert shown["photo_ref"] == "key/1.jpg"
    assert shown["schedule_visible"] is True


def test_content_scope_is_consent_gated() -> None:
    """Content participation scope is cast content — gated, not an operational flag.

    Regression (Codex R1 HIGH): with only the name granted, content_scope stays
    hidden until ConsentScope.CONTENT_SCOPE is granted.
    """
    profile, manager = _published_profile_with_name()
    update_cast_profile(profile=profile, actor=manager, content_scope="라이브, 굿즈 제작")

    shown = public_profile(profile)
    assert shown is not None
    # Name granted, content scope withheld → hidden.
    assert shown["content_scope"] == ""

    record_cast_consent(
        profile=profile,
        scope=ConsentScope.CONTENT_SCOPE.value,
        status=ConsentStatus.GRANTED.value,
        actor=manager,
    )
    shown = public_profile(profile)
    assert shown is not None
    assert shown["content_scope"] == "라이브, 굿즈 제작"


def test_refused_consent_keeps_field_hidden() -> None:
    """An explicit refusal hides the field exactly like withheld (fail-closed)."""
    profile, manager = _published_profile_with_name()
    record_cast_consent(
        profile=profile,
        scope=ConsentScope.PROFILE_PHOTO.value,
        status=ConsentStatus.REFUSED.value,
        actor=manager,
    )
    shown = public_profile(profile)
    assert shown is not None
    assert shown["photo_ref"] == ""


def test_record_consent_upserts_single_row_per_scope() -> None:
    """Re-recording a scope updates it in place (one current state per scope)."""
    profile, manager = _published_profile_with_name()
    record_cast_consent(
        profile=profile,
        scope=ConsentScope.STAGE_NAME.value,
        status=ConsentStatus.REFUSED.value,
        actor=manager,
    )
    rows = CastConsent.objects.filter(profile=profile, scope=ConsentScope.STAGE_NAME.value)
    assert rows.count() == 1
    assert rows.get().status == ConsentStatus.REFUSED.value
    # Name now refused → whole profile hidden again.
    assert public_profile(profile) is None
    # The scope/status pair is captured in the audit metadata.
    entry = AuditEntry.objects.filter(action=AuditAction.CAST_CONSENT_RECORDED.value).first()
    assert entry is not None
    assert entry.metadata["scope"] == ConsentScope.STAGE_NAME.value


def test_record_consent_rejects_unknown_scope_or_status() -> None:
    """Unknown scope/status values are refused (closed enums)."""
    profile, manager = _published_profile_with_name()
    with pytest.raises(CastProfileError):
        record_cast_consent(
            profile=profile, scope="bogus", status=ConsentStatus.GRANTED.value, actor=manager
        )
    with pytest.raises(CastProfileError):
        record_cast_consent(
            profile=profile,
            scope=ConsentScope.SCHEDULE.value,
            status="maybe",
            actor=manager,
        )


def test_view_public_profile_emits_clean_impression_event() -> None:
    """A fan view records cast_profile_viewed with the cast id only — no content."""
    profile, _ = _published_profile_with_name()
    update_cast_profile(
        profile=profile,
        actor=_operator(),
        intro=_INTRO,
        photo_ref="key/secret.jpg",
    )
    fan = _fan()

    shown = view_public_profile(profile=profile, viewer=fan)
    assert shown is not None

    event = EventRecord.objects.get(event_name=EventName.CAST_PROFILE_VIEWED.value)
    assert event.actor_type == ActorType.FAN.value
    assert event.actor_is_operator is False
    assert event.cast_id == str(profile.id)
    assert event.fan_id == str(fan.fan_id)
    assert event.payload == {"cast_id": str(profile.id)}
    # No profile content rides the append-only ledger.
    serialised = str(event.payload) + str(event.ids) + str(event.context)
    assert _STAGE_NAME not in serialised
    assert "secret.jpg" not in serialised


def test_view_hidden_profile_emits_no_event() -> None:
    """Viewing a hidden profile returns None and records no impression."""
    operator = _operator()
    profile = create_cast_profile(stage_name=_STAGE_NAME, actor=operator)
    assert view_public_profile(profile=profile, viewer=_fan()) is None
    assert not EventRecord.objects.filter(event_name=EventName.CAST_PROFILE_VIEWED.value).exists()
