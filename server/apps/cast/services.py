"""Cast profile + consent services (ASS-92, F04).

The load-bearing rule is the **fail-closed consent gate**: ``public_profile``
returns only the fields whose scope a manager has explicitly ``granted`` (and
only when the operator has published the profile). Everything else is hidden, so
a cast whose consent is missing renders as an empty slot rather than a leak.

The platform does not decide consent (CONSTRAINTS L91); ``record_cast_consent``
persists the state an authorised manager entered from the contract/onboarding
gate, audited, and the gate enforces it. ``view_public_profile`` is the only
producer of the ``cast_profile_viewed`` event, emitted via the sanctioned
``emit_event`` funnel with the cast id only — no profile content rides the
append-only ledger.
"""

from __future__ import annotations

from typing import TypedDict

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.cast.models import (
    CastConsent,
    CastProfile,
    ConsentScope,
    ConsentStatus,
    ProfileVisibility,
)
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import emit_event
from apps.identity.models import Account


class CastProfileError(Exception):
    """Raised when a cast profile or consent operation is invalid."""


class PublicProfile(TypedDict):
    """The fan-visible projection of a profile (consent-gated fields only)."""

    cast_id: str
    stage_name: str
    intro: str
    photo_ref: str
    schedule_visible: bool
    cheki_available: bool
    content_scope: str


@transaction.atomic
def create_cast_profile(
    *,
    stage_name: str,
    actor: Account,
    intro: str = "",
    photo_ref: str = "",
    cheki_available: bool = False,
    content_scope: str = "",
) -> CastProfile:
    """Create a hidden cast profile (operator+); audited.

    The profile starts ``PRIVATE`` with no consent rows, so it is fully hidden
    from fans until a manager grants the relevant scopes and an operator
    publishes it — the fail-closed default.
    """
    if not stage_name.strip():
        raise CastProfileError("stage_name is required.")
    profile = CastProfile.objects.create(
        stage_name=stage_name,
        intro=intro,
        photo_ref=photo_ref,
        cheki_available=cheki_available,
        content_scope=content_scope,
        visibility=ProfileVisibility.PRIVATE.value,
        created_by=actor,
    )
    record_audit(
        actor=actor,
        action=AuditAction.CAST_PROFILE_CREATED.value,
        target=str(profile.id),
    )
    return profile


@transaction.atomic
def update_cast_profile(
    *,
    profile: CastProfile,
    actor: Account,
    stage_name: str | None = None,
    intro: str | None = None,
    photo_ref: str | None = None,
    cheki_available: bool | None = None,
    content_scope: str | None = None,
    visibility: str | None = None,
) -> CastProfile:
    """Update profile content and/or the publish toggle (operator+); audited.

    Each argument left ``None`` is unchanged. ``visibility`` only flips the
    operator publish control; it never exposes a field whose consent is missing
    (the gate still applies on read).
    """
    if visibility is not None and visibility not in ProfileVisibility.values:
        raise CastProfileError(f"Unknown visibility '{visibility}'.")
    if stage_name is not None:
        if not stage_name.strip():
            raise CastProfileError("stage_name cannot be blank.")
        profile.stage_name = stage_name
    if intro is not None:
        profile.intro = intro
    if photo_ref is not None:
        profile.photo_ref = photo_ref
    if cheki_available is not None:
        profile.cheki_available = cheki_available
    if content_scope is not None:
        profile.content_scope = content_scope
    if visibility is not None:
        profile.visibility = visibility
    profile.save()
    record_audit(
        actor=actor,
        action=AuditAction.CAST_PROFILE_UPDATED.value,
        target=str(profile.id),
    )
    return profile


@transaction.atomic
def record_cast_consent(
    *,
    profile: CastProfile,
    scope: str,
    status: str,
    actor: Account,
    note: str = "",
) -> CastConsent:
    """Record (or update) one scope's consent state (manager+); audited.

    Consent is the portrait-rights gate, so it is manager-gated like a block:
    operators prepare profile content, a manager records what the cast agreed to.
    Upserts on ``(profile, scope)`` so a scope has a single current state; the
    scope/status pair is captured in the audit metadata for the history.
    """
    if scope not in ConsentScope.values:
        raise CastProfileError(f"Unknown consent scope '{scope}'.")
    if status not in ConsentStatus.values:
        raise CastProfileError(f"Unknown consent status '{status}'.")
    consent, _ = CastConsent.objects.update_or_create(
        profile=profile,
        scope=scope,
        defaults={"status": status, "note": note, "recorded_by": actor},
    )
    record_audit(
        actor=actor,
        action=AuditAction.CAST_CONSENT_RECORDED.value,
        target=str(profile.id),
        metadata={"scope": scope, "status": status},
    )
    return consent


def consent_map(profile: CastProfile) -> dict[str, str]:
    """Return every scope's status, defaulting missing scopes to ``WITHHELD``.

    The default is the fail-closed value so a scope a manager has never touched
    reads as withheld (hidden), not granted.
    """
    statuses = {scope: ConsentStatus.WITHHELD.value for scope in ConsentScope.values}
    for consent in profile.consents.all():
        statuses[consent.scope] = consent.status
    return statuses


def _is_granted(statuses: dict[str, str], scope: str) -> bool:
    """Return whether ``scope`` is explicitly granted (fail-closed otherwise)."""
    return statuses.get(scope) == ConsentStatus.GRANTED.value


def public_profile(profile: CastProfile) -> PublicProfile | None:
    """Project the fan-visible view of a profile, or ``None`` if it is hidden.

    Fail-closed: the profile is shown only when it is ``PUBLIC`` *and* the stage
    name is granted (a profile cannot be shown without a name a fan may see).
    Within a shown profile each cast-attributable field is independently gated —
    an unconsented photo, intro, or content scope is withheld even though the
    name is visible. ``cheki_available`` is an operational availability flag
    (operator-controlled, not the cast's likeness), so it alone rides along.
    """
    statuses = consent_map(profile)
    if profile.visibility != ProfileVisibility.PUBLIC.value:
        return None
    if not _is_granted(statuses, ConsentScope.STAGE_NAME.value):
        return None
    photo_ok = _is_granted(statuses, ConsentScope.PROFILE_PHOTO.value)
    intro_ok = _is_granted(statuses, ConsentScope.PROFILE_INTRO.value)
    content_ok = _is_granted(statuses, ConsentScope.CONTENT_SCOPE.value)
    return {
        "cast_id": str(profile.id),
        "stage_name": profile.stage_name,
        "intro": profile.intro if intro_ok else "",
        "photo_ref": profile.photo_ref if photo_ok else "",
        "schedule_visible": _is_granted(statuses, ConsentScope.SCHEDULE.value),
        "cheki_available": profile.cheki_available,
        "content_scope": profile.content_scope if content_ok else "",
    }


@transaction.atomic
def view_public_profile(
    *,
    profile: CastProfile,
    viewer: Account,
) -> PublicProfile | None:
    """Return the gated public view and record a ``cast_profile_viewed`` event.

    Returns ``None`` when the profile is not publicly visible (the caller maps
    that to 404 so a hidden/unconsented profile's existence is not revealed). The
    impression event carries only the cast id; no profile content reaches the
    ledger.
    """
    public = public_profile(profile)
    if public is None:
        return None
    fan_id = str(viewer.fan_id)
    emit_event(
        event_name=EventName.CAST_PROFILE_VIEWED.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.FAN.value,
        source=EventSource.FAN_APP.value,
        actor_id=fan_id,
        fan_id=fan_id,
        cast_id=str(profile.id),
        actor_is_operator=False,
        ids={"cast_id": str(profile.id)},
        payload={"cast_id": str(profile.id)},
    )
    return public
