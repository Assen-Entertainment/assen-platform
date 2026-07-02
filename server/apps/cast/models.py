"""Domain models for cast profiles + portrait-rights consent (ASS-92, F04).

A cast profile is operator-managed data (the cast has no account in P0). Two
rules from Company-OS shape the design:

1. **Consent is per-scope and fail-closed.** Portrait rights are not one
   checkbox (``Cast_Contract_Settlement_Portrait_Checklist`` §7 동의 매트릭스):
   the stage name, profile photo, intro, and schedule each have their own
   consent, defaulting to *withheld*. A field is exposed publicly ONLY when its
   scope is explicitly ``granted`` — absence of a consent row means hidden, so a
   profile a cast has not agreed to publish renders as an empty slot, never a
   leak. The platform never *decides* consent (CONSTRAINTS L91 캐스트 동의 =
   승인 필요); it records the state an authorised manager entered from the
   contract/onboarding gate and enforces it as data.
2. **Profiles are not deleted, only unpublished.** ``visibility`` toggles the
   operator publish control; rights/consent history and the cast_profile_viewed
   ledger must survive, so there is no hard delete (mirrors safety's never-delete
   rule).

Models land in this app per the narrow-boundary rule (CONSTRAINTS #38); the
server is migration-less (tables via ``migrate --run-syncdb``), so no migration
files are created here.
"""

from __future__ import annotations

import uuid

from django.db import models


class ConsentScope(models.TextChoices):
    """The separable portrait-rights scopes a profile field is gated on.

    Each maps to a row in the ``Cast_Contract_Settlement_Portrait_Checklist`` §7
    매트릭스 whose default is 보류 (withheld). Scopes are deliberately granular:
    consenting to show a stage name is not consenting to show a photo. Every
    cast-attributable display field has a scope — including the content
    participation scope (콘텐츠 참여 범위), which is profile content the issue
    requires to stay within consent, not an operational flag.
    """

    STAGE_NAME = "stage_name", "stage_name"
    PROFILE_PHOTO = "profile_photo", "profile_photo"
    PROFILE_INTRO = "profile_intro", "profile_intro"
    SCHEDULE = "schedule", "schedule"
    CONTENT_SCOPE = "content_scope", "content_scope"


class ConsentStatus(models.TextChoices):
    """Consent state for one scope; only ``GRANTED`` exposes the field.

    ``WITHHELD`` is the fail-closed default (보류) and ``REFUSED`` is an explicit
    no (거절) — both hide the field, but the distinction is kept so an operator
    can tell "not yet asked" from "asked and declined".
    """

    WITHHELD = "withheld", "withheld"
    GRANTED = "granted", "granted"
    REFUSED = "refused", "refused"


class ProfileVisibility(models.TextChoices):
    """Operator publish control, layered on top of consent.

    A profile is publicly visible only when it is ``PUBLIC`` *and* the relevant
    scope is granted — visibility never overrides a missing consent. Defaults to
    ``PRIVATE`` so a freshly created profile is hidden until deliberately
    published.
    """

    PRIVATE = "private", "private"
    PUBLIC = "public", "public"


class CastProfile(models.Model):
    """An operator-managed cast profile; field exposure is consent-gated.

    The content (stage name, intro, photo reference, operational flags) is always
    stored so operators can prepare a profile before consent is recorded; what
    *fans* see is computed by the consent gate in ``services.public_profile``.
    ``photo_ref`` is an object-storage key only — the access-controlled binary
    upload is a follow-up (v1), so v0 carries the reference without serving bytes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stage_name = models.CharField(max_length=120)
    intro = models.TextField(blank=True, default="")
    # Object-storage key for the portrait; binary upload/serving lands in v1.
    photo_ref = models.CharField(max_length=512, blank=True, default="")
    # An operational availability flag (whether the store offers a cheki with
    # this cast) — operator-controlled, not the cast's likeness, so it rides
    # along once the profile is public with no separate consent scope.
    cheki_available = models.BooleanField(default=False)
    # Cast-attributable display content (콘텐츠 참여 범위): consent-gated by
    # ConsentScope.CONTENT_SCOPE, withheld until granted (the issue requires
    # profile content to stay within consent).
    content_scope = models.CharField(max_length=255, blank=True, default="")
    visibility = models.CharField(
        max_length=16,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PRIVATE,
    )
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_cast_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["visibility", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the profile by id/visibility (stage name may be unconsented)."""
        return f"cast_profile:{self.id}:{self.visibility}"


class CastConsent(models.Model):
    """One scope's consent state for a profile, recorded by a manager.

    Unique per ``(profile, scope)`` so each scope has a single current state;
    re-recording updates it in place (the audit trail carries the history). A
    scope with no row is treated as ``WITHHELD`` by the gate, so the default is
    hidden even before any consent is entered.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        CastProfile,
        on_delete=models.PROTECT,
        related_name="consents",
    )
    scope = models.CharField(max_length=32, choices=ConsentScope.choices)
    status = models.CharField(
        max_length=16,
        choices=ConsentStatus.choices,
        default=ConsentStatus.WITHHELD,
    )
    # Optional internal pointer to the signed consent record (no PII in the body).
    note = models.CharField(max_length=255, blank=True, default="")
    recorded_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="recorded_cast_consents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "scope"],
                name="uniq_cast_consent_profile_scope",
            ),
        ]
        indexes = [
            models.Index(fields=["profile", "scope"]),
        ]
        ordering = ["scope"]

    def __str__(self) -> str:
        """Identify the consent by profile/scope/status."""
        return f"cast_consent:{self.profile_id}:{self.scope}/{self.status}"
