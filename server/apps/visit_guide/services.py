"""Service layer for the visit guide CMS (F02, ASS-101 v0).

Every mutation passes through this module so the operational row and the audit
trail stay coupled. Publication is the fail-closed "승인 전 비공개" gate: a section
is public only while ``status=published``, and editing is **draft-only** so
unapproved copy cannot be mutated into a published section in place (mirrors the
event_campaign approval gate, ASS-107).

The usage-rules acknowledgement records the fan's consent against the published
rules **version** via the consent app (``rule_consent_given``); republishing the
rules bumps the version, so an old acknowledgement no longer satisfies the gate.

No price/menu money figure is stored or accepted here — the approved price values
are a separate, approval-gated deferred slice (issue Blocker; CONSTRAINTS L91).
"""

from __future__ import annotations

from django.db import IntegrityError, transaction

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.consent.models import ConsentKind
from apps.consent.services import record_consent
from apps.identity.models import Account, Role
from apps.visit_guide.models import (
    DEFAULT_STORE_ID,
    GuideSection,
    GuideSectionType,
    GuideStatus,
)

_TITLE_MAX = 200
_BODY_MAX = 8000


class StaleRulesError(ValueError):
    """The acknowledged rules version is no longer the published one (reload needed)."""


# --------------------------------------------------------------------------- #
# Operator: section lifecycle
# --------------------------------------------------------------------------- #
@transaction.atomic
def create_section(
    *,
    actor: Account,
    section_type: str,
    title: str,
    body: str = "",
    display_order: int = 0,
    store_id: str = DEFAULT_STORE_ID,
) -> GuideSection:
    """Create a guide section as a draft (non-public until published).

    Exactly one section per ``(store_id, section_type)``; a duplicate is rejected
    so the guide keeps a single canonical section per type.
    """
    if section_type not in GuideSectionType.values:
        raise ValueError("Unknown section_type.")
    if not title.strip():
        raise ValueError("title is required.")
    _check_body(body)
    try:
        with transaction.atomic():
            section = GuideSection.objects.create(
                section_type=section_type,
                title=title.strip(),
                body=body.strip(),
                display_order=display_order,
                store_id=store_id,
                created_by=actor,
            )
    except IntegrityError as exc:
        raise ValueError("A guide section of this type already exists.") from exc
    _audit(actor, AuditAction.GUIDE_SECTION_CREATED.value, section)
    return section


@transaction.atomic
def update_section(
    *,
    section: GuideSection,
    actor: Account,
    title: str | None = None,
    body: str | None = None,
    display_order: int | None = None,
) -> GuideSection:
    """Edit a draft section; only supplied fields change.

    Draft-only: publishing is the approval gate, so a published section cannot be
    mutated in place (which would let unapproved copy reach the public surface).
    To change a published section, unpublish it, edit, then republish.
    """
    section = _lock(section)
    if section.status != GuideStatus.DRAFT.value:
        raise ValueError("Only a draft section can be edited; unpublish it first.")
    fields: list[str] = []
    if title is not None:
        if not title.strip():
            raise ValueError("title is required.")
        section.title = title.strip()
        fields.append("title")
    if body is not None:
        _check_body(body)
        section.body = body.strip()
        fields.append("body")
    if display_order is not None:
        section.display_order = display_order
        fields.append("display_order")
    if not fields:
        raise ValueError("No section fields to update.")
    section.save(update_fields=[*fields, "updated_at"])
    _audit(actor, AuditAction.GUIDE_SECTION_UPDATED.value, section, metadata={"changed": fields})
    return section


@transaction.atomic
def publish_section(*, section: GuideSection, actor: Account) -> GuideSection:
    """Publish a draft section (the 공개 gate). Bumps the version."""
    section = _lock(section)
    if section.status != GuideStatus.DRAFT.value:
        raise ValueError(f"Cannot publish a section in status '{section.status}'.")
    section.status = GuideStatus.PUBLISHED.value
    section.version += 1
    section.save(update_fields=["status", "version", "updated_at"])
    _audit(actor, AuditAction.GUIDE_SECTION_PUBLISHED.value, section)
    return section


@transaction.atomic
def unpublish_section(*, section: GuideSection, actor: Account) -> GuideSection:
    """Return a published section to draft (비공개)."""
    section = _lock(section)
    if section.status != GuideStatus.PUBLISHED.value:
        raise ValueError(f"Cannot unpublish a section in status '{section.status}'.")
    section.status = GuideStatus.DRAFT.value
    section.save(update_fields=["status", "updated_at"])
    _audit(actor, AuditAction.GUIDE_SECTION_UNPUBLISHED.value, section)
    return section


# --------------------------------------------------------------------------- #
# Fan: rule acknowledgement
# --------------------------------------------------------------------------- #
@transaction.atomic
def acknowledge_rules(
    *, fan: Account, expected_version: int, store_id: str = DEFAULT_STORE_ID
) -> int:
    """Record a fan's consent to the rules version the fan actually read.

    Reuses the consent app: ``record_consent(kind=rule, version=<rules version>)``
    persists the grant and emits ``rule_consent_given``. ``expected_version`` is
    the version the fan saw (from the public read); the consent is recorded only
    if it still matches the currently-published rules. If the rules were
    republished in between (version moved on), this raises :class:`StaleRulesError`
    so the client reloads and re-reads — a stale acknowledgement must never record
    consent for a version the fan never saw. Returns the acknowledged version.
    Raises if the usage rules are not published or the caller is not a fan.
    """
    if fan.role != Role.FAN.value:
        raise ValueError("Only fans can acknowledge the rules.")
    rules = (
        GuideSection.objects.filter(
            store_id=store_id,
            section_type=GuideSectionType.USAGE_RULES.value,
            status=GuideStatus.PUBLISHED.value,
        )
        .select_for_update()
        .first()
    )
    if rules is None:
        raise ValueError("The usage rules are not published yet.")
    if rules.version != expected_version:
        raise StaleRulesError("The usage rules have changed; reload before acknowledging.")
    record_consent(account=fan, kind=ConsentKind.RULE.value, version=str(rules.version))
    return rules.version


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _lock(section: GuideSection) -> GuideSection:
    """Re-load the section under a row lock so concurrent transitions serialise."""
    return GuideSection.objects.select_for_update().get(pk=section.pk)


def _check_body(body: str) -> None:
    """Bound the body length (no echo of the content)."""
    if len(body) > _BODY_MAX:
        raise ValueError("body is too long.")


def _audit(
    actor: Account,
    action: str,
    section: GuideSection,
    *,
    metadata: dict[str, object] | None = None,
) -> None:
    """Write the audit entry for an operator section mutation."""
    entry_metadata: dict[str, object] = {
        "section_type": section.section_type,
        "status": section.status,
        "version": section.version,
    }
    if metadata:
        entry_metadata.update(metadata)
    record_audit(
        actor=actor,
        action=action,
        target=str(section.id),
        metadata=entry_metadata,
    )
