"""Cast profile API (ASS-92, F04): operator CRUD + manager consent + fan view.

Three access tiers:

- **operator+** create, list, read, and edit profile content and the publish
  toggle (``operator_required``).
- **manager+** record the per-scope portrait-rights consent — the rights gate is
  manager-gated like a block, so an operator can prepare a profile but only a
  manager grants what fans may see (``manager_required``).
- **fan** read the consent-gated public view; a hidden/unconsented profile 404s
  so its existence is not revealed, and a view records ``cast_profile_viewed``.

No tokens are issued here and the staff/fan auth classes are reused as-is, so
this stays an ordinary business surface (not auth code, CONSTRAINTS #26).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import manager_required, operator_required
from apps.cast.models import CastProfile
from apps.cast.services import (
    CastProfileError,
    consent_map,
    create_cast_profile,
    record_cast_consent,
    update_cast_profile,
    view_public_profile,
)
from apps.identity.auth import FanBearerAuth, authed
from apps.identity.models import Account, Role
from config.api import api
from config.throttle import user_write_throttle

router = Router(tags=["cast"])

_NAME_MAX = 120
_REF_MAX = 512
_SCOPE_MAX = 255


class CastError(Schema):
    """Stable error shape for cast endpoints."""

    detail: str


class CastProfileCreateIn(Schema):
    """Operator profile-creation payload (content only; starts hidden)."""

    stage_name: str = Field(max_length=_NAME_MAX)
    intro: str = Field(default="", max_length=2000)
    photo_ref: str = Field(default="", max_length=_REF_MAX)
    cheki_available: bool = False
    content_scope: str = Field(default="", max_length=_SCOPE_MAX)


class CastProfileUpdateIn(Schema):
    """Partial update; any field left unset is unchanged."""

    stage_name: str | None = Field(default=None, max_length=_NAME_MAX)
    intro: str | None = Field(default=None, max_length=2000)
    photo_ref: str | None = Field(default=None, max_length=_REF_MAX)
    cheki_available: bool | None = None
    content_scope: str | None = Field(default=None, max_length=_SCOPE_MAX)
    visibility: str | None = None


class CastConsentIn(Schema):
    """Manager consent record for one scope."""

    scope: str = Field(max_length=32)
    status: str = Field(max_length=16)
    note: str = Field(default="", max_length=_SCOPE_MAX)


class CastProfileOut(Schema):
    """Operator-facing profile, including the per-scope consent map.

    Operators see the full content and every scope's consent state so they can
    tell what a fan would and would not see; the fan-facing projection is a
    separate schema (``CastPublicProfileOut``).
    """

    cast_id: str
    stage_name: str
    intro: str
    photo_ref: str
    cheki_available: bool
    content_scope: str
    visibility: str
    consents: dict[str, str]
    created_at: datetime


class CastPublicProfileOut(Schema):
    """Fan-facing projection: only consent-granted fields are populated."""

    cast_id: str
    stage_name: str
    intro: str
    photo_ref: str
    schedule_visible: bool
    cheki_available: bool
    content_scope: str


def _actor(request: HttpRequest) -> Account:
    """Return the authenticated staff account supplied by RoleRequired."""
    # request.auth is untyped without Ninja stubs (same idiom as safety/api.py).
    return authed(request)


def _fan_account(request: HttpRequest) -> Account:
    """Return the authenticated fan account supplied by FanBearerAuth."""
    return authed(request)


def _operator_out(profile: CastProfile) -> CastProfileOut:
    """Serialise a profile with its consent map for an operator response."""
    return CastProfileOut(
        cast_id=str(profile.id),
        stage_name=profile.stage_name,
        intro=profile.intro,
        photo_ref=profile.photo_ref,
        cheki_available=profile.cheki_available,
        content_scope=profile.content_scope,
        visibility=profile.visibility,
        consents=consent_map(profile),
        created_at=profile.created_at,
    )


@router.post(
    "/profiles",
    auth=operator_required,
    response={201: CastProfileOut, 422: CastError},
    throttle=user_write_throttle("20/min"),
)
def create_profile(
    request: HttpRequest,
    payload: CastProfileCreateIn,
) -> tuple[int, CastProfileOut | CastError]:
    """Create a cast profile (operator+); it starts private and fully hidden."""
    try:
        profile = create_cast_profile(
            stage_name=payload.stage_name,
            intro=payload.intro,
            photo_ref=payload.photo_ref,
            cheki_available=payload.cheki_available,
            content_scope=payload.content_scope,
            actor=_actor(request),
        )
    except CastProfileError as exc:
        return 422, CastError(detail=str(exc))
    return 201, _operator_out(profile)


@router.get(
    "/profiles",
    auth=operator_required,
    response={200: list[CastProfileOut]},
)
def list_profiles(
    request: HttpRequest,
    limit: int = 200,
) -> list[CastProfileOut]:
    """List profiles with their consent state (operator+), bounded by ``limit``."""
    del request
    capped = max(1, min(limit, 500))
    profiles = CastProfile.objects.prefetch_related("consents")[:capped]
    return [_operator_out(profile) for profile in profiles]


@router.get(
    "/profiles/{cast_id}",
    auth=operator_required,
    response={200: CastProfileOut, 404: CastError},
)
def get_profile(
    request: HttpRequest,
    cast_id: uuid.UUID,
) -> CastProfileOut:
    """Read one profile with its consent state (operator+)."""
    del request
    profile = get_object_or_404(CastProfile.objects.prefetch_related("consents"), id=cast_id)
    return _operator_out(profile)


@router.patch(
    "/profiles/{cast_id}",
    auth=operator_required,
    response={200: CastProfileOut, 404: CastError, 422: CastError},
    throttle=user_write_throttle("30/min"),
)
def patch_profile(
    request: HttpRequest,
    cast_id: uuid.UUID,
    payload: CastProfileUpdateIn,
) -> tuple[int, CastProfileOut | CastError]:
    """Update profile content and/or the publish toggle (operator+)."""
    profile = get_object_or_404(CastProfile, id=cast_id)
    try:
        update_cast_profile(
            profile=profile,
            actor=_actor(request),
            stage_name=payload.stage_name,
            intro=payload.intro,
            photo_ref=payload.photo_ref,
            cheki_available=payload.cheki_available,
            content_scope=payload.content_scope,
            visibility=payload.visibility,
        )
    except CastProfileError as exc:
        return 422, CastError(detail=str(exc))
    profile = get_object_or_404(CastProfile.objects.prefetch_related("consents"), id=cast_id)
    return 200, _operator_out(profile)


@router.post(
    "/profiles/{cast_id}/consent",
    auth=manager_required,
    response={200: CastProfileOut, 404: CastError, 422: CastError},
    throttle=user_write_throttle("30/min"),
)
def record_consent(
    request: HttpRequest,
    cast_id: uuid.UUID,
    payload: CastConsentIn,
) -> tuple[int, CastProfileOut | CastError]:
    """Record one scope's portrait-rights consent (manager+).

    The rights gate is manager-gated: operators ready a profile, a manager grants
    what fans may see, reflecting that cast consent is not an operator decision.
    """
    profile = get_object_or_404(CastProfile, id=cast_id)
    try:
        record_cast_consent(
            profile=profile,
            scope=payload.scope,
            status=payload.status,
            actor=_actor(request),
            note=payload.note,
        )
    except CastProfileError as exc:
        return 422, CastError(detail=str(exc))
    profile = get_object_or_404(CastProfile.objects.prefetch_related("consents"), id=cast_id)
    return 200, _operator_out(profile)


@router.get(
    "/public-profiles/{cast_id}",
    auth=[FanBearerAuth()],
    response={200: CastPublicProfileOut, 403: CastError, 404: CastError},
)
def view_public_cast_profile(
    request: HttpRequest,
    cast_id: uuid.UUID,
) -> tuple[int, CastPublicProfileOut | CastError]:
    """Read the consent-gated public view as a fan; records an impression.

    FanBearerAuth is role-agnostic, so a FAN role is required (a staff token must
    not be logged as a fan impression — the cast_profile_viewed metric would be
    polluted; mirrors the ASS-110 fan gate). A hidden or unconsented profile 404s
    so its existence is not disclosed.
    """
    fan = _fan_account(request)
    if fan.role != Role.FAN.value:
        return 403, CastError(detail="Only fans can view cast profiles here.")
    profile = get_object_or_404(CastProfile, id=cast_id)
    public = view_public_profile(profile=profile, viewer=fan)
    if public is None:
        return 404, CastError(detail="Cast profile not found.")
    return 200, CastPublicProfileOut(
        cast_id=public["cast_id"],
        stage_name=public["stage_name"],
        intro=public["intro"],
        photo_ref=public["photo_ref"],
        schedule_visible=public["schedule_visible"],
        cheki_available=public["cheki_available"],
        content_scope=public["content_scope"],
    )


api.add_router("/cast", router)
