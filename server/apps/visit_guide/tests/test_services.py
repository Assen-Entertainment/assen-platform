"""Tests for the visit-guide service (F02, ASS-101 v0).

Covers the operator lifecycle (create/update/publish/unpublish, draft-only edit,
one-per-type, version bump) and the fan rule acknowledgement (consent record +
``rule_consent_given`` event, version invalidation on republish).
"""

from __future__ import annotations

import pytest

from apps.consent.models import ConsentKind, ConsentRecord
from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account, Role
from apps.visit_guide.models import GuideSection, GuideSectionType, GuideStatus
from apps.visit_guide.services import (
    StaleRulesError,
    acknowledge_rules,
    create_section,
    publish_section,
    unpublish_section,
    update_section,
)

pytestmark = pytest.mark.django_db

RULES = GuideSectionType.USAGE_RULES.value
GUIDE = GuideSectionType.FIRST_VISIT_GUIDE.value


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _operator() -> Account:
    """Create an operator account (the section author)."""
    return _account(Role.OPERATOR.value)


def _fan() -> Account:
    """Create a fan account."""
    return _account(Role.FAN.value)


def test_create_section_starts_as_draft() -> None:
    """A new section is a draft at version 0."""
    section = create_section(actor=_operator(), section_type=RULES, title="이용 규칙")
    assert section.status == GuideStatus.DRAFT.value
    assert section.version == 0


def test_create_rejects_unknown_type_blank_title_and_duplicate() -> None:
    """Unknown type, blank title, and a duplicate per type are all rejected."""
    op = _operator()
    with pytest.raises(ValueError):
        create_section(actor=op, section_type="nope", title="x")
    with pytest.raises(ValueError):
        create_section(actor=op, section_type=RULES, title="   ")
    create_section(actor=op, section_type=RULES, title="이용 규칙")
    with pytest.raises(ValueError):
        create_section(actor=op, section_type=RULES, title="중복")


def test_publish_bumps_version_and_makes_public() -> None:
    """Publishing a draft sets it published and increments the version."""
    op = _operator()
    section = create_section(actor=op, section_type=RULES, title="이용 규칙")
    published = publish_section(section=section, actor=op)
    assert published.status == GuideStatus.PUBLISHED.value
    assert published.version == 1


def test_published_section_cannot_be_edited_in_place() -> None:
    """A published section is draft-only for edits (approval-gate integrity)."""
    op = _operator()
    section = publish_section(
        section=create_section(actor=op, section_type=RULES, title="이용 규칙"), actor=op
    )
    with pytest.raises(ValueError):
        update_section(section=section, actor=op, title="몰래 수정")


def test_unpublish_then_edit_then_republish_bumps_version_again() -> None:
    """Unpublish enables editing; republishing bumps the version a second time."""
    op = _operator()
    section = publish_section(
        section=create_section(actor=op, section_type=RULES, title="v1"), actor=op
    )
    assert section.version == 1
    unpublish_section(section=section, actor=op)
    update_section(section=section, actor=op, body="개정된 규칙")
    republished = publish_section(section=GuideSection.objects.get(pk=section.pk), actor=op)
    assert republished.version == 2


def test_update_requires_a_field_and_publish_guards_status() -> None:
    """Empty update and double publish/unpublish are rejected."""
    op = _operator()
    draft = create_section(actor=op, section_type=GUIDE, title="가이드")
    with pytest.raises(ValueError):
        update_section(section=draft, actor=op)
    with pytest.raises(ValueError):
        unpublish_section(section=draft, actor=op)  # not published
    publish_section(section=draft, actor=op)
    # Re-publishing an already-published section is rejected.
    with pytest.raises(ValueError):
        publish_section(section=GuideSection.objects.get(pk=draft.pk), actor=op)


def test_acknowledge_rules_records_consent_and_emits_event() -> None:
    """A fan ack writes a RULE ConsentRecord and a rule_consent_given event."""
    op = _operator()
    fan = _fan()
    publish_section(
        section=create_section(actor=op, section_type=RULES, title="이용 규칙"), actor=op
    )
    version = acknowledge_rules(fan=fan, expected_version=1)
    assert version == 1
    assert ConsentRecord.objects.filter(
        account=fan, kind=ConsentKind.RULE.value, version="1"
    ).exists()
    assert EventRecord.objects.filter(event_name=EventName.RULE_CONSENT_GIVEN.value).count() == 1


def test_acknowledge_rules_requires_published_rules_and_fan() -> None:
    """Ack is refused when no rules are published, and for a non-fan caller."""
    op = _operator()
    fan = _fan()
    with pytest.raises(ValueError):
        acknowledge_rules(fan=fan, expected_version=1)  # nothing published yet
    publish_section(
        section=create_section(actor=op, section_type=RULES, title="이용 규칙"), actor=op
    )
    with pytest.raises(ValueError):
        acknowledge_rules(fan=op, expected_version=1)  # operator is not a fan


def test_stale_version_ack_is_refused_and_records_no_consent() -> None:
    """A fan ack for a version that is no longer published is refused (no consent).

    Read v1, operator republishes v2, the fan submits a stale ack for v1: the
    consent must NOT be recorded for v2 (the version the fan never saw).
    """
    op = _operator()
    fan = _fan()
    section = publish_section(
        section=create_section(actor=op, section_type=RULES, title="v1"), actor=op
    )
    unpublish_section(section=section, actor=op)
    update_section(section=section, actor=op, body="개정")
    publish_section(section=GuideSection.objects.get(pk=section.pk), actor=op)  # now v2

    with pytest.raises(StaleRulesError):
        acknowledge_rules(fan=fan, expected_version=1)  # stale: fan saw v1
    assert not ConsentRecord.objects.filter(account=fan, kind=ConsentKind.RULE.value).exists()


def test_republish_then_fresh_ack_binds_to_new_version() -> None:
    """After a republish, a fresh ack for the new version records consent for it."""
    op = _operator()
    fan = _fan()
    section = publish_section(
        section=create_section(actor=op, section_type=RULES, title="v1"), actor=op
    )
    assert acknowledge_rules(fan=fan, expected_version=1) == 1
    unpublish_section(section=section, actor=op)
    update_section(section=section, actor=op, body="개정")
    publish_section(section=GuideSection.objects.get(pk=section.pk), actor=op)
    assert acknowledge_rules(fan=fan, expected_version=2) == 2
    assert ConsentRecord.objects.filter(
        account=fan, kind=ConsentKind.RULE.value, version="2"
    ).exists()
