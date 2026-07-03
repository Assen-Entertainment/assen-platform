"""Visit guide API (F02, ASS-101 v0).

Three surfaces:
- **operator** (``operator_required``): create / list (all statuses) / detail /
  update (draft-only) / publish / unpublish guide sections.
- **public** (no auth): list and read **published** sections. The pre-visit guide
  (이용 규칙·첫 방문 가이드 …) is meant to be read *before* signup
  (PRD 첫 방문 전 여정), and it exposes only published, PII-free content with no
  money figure — so it is intentionally unauthenticated. A draft id is a 404 (no
  existence leak).
- **fan** (``FanBearerAuth`` — bearer only, role-gated): acknowledge the published
  usage-rules version (records ``rule_consent_given`` via the consent app).
  Bearer-only because a state-changing fan POST over the web cookie surface needs
  CSRF (ADR-0002), not yet wired (ASS-110 stance).

No price/menu value is stored or exposed — the approved price values are the
approval-gated, deferred slice (issue Blocker; CONSTRAINTS L91).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import cast

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import operator_required
from apps.identity.auth import FanBearerAuth
from apps.identity.models import Account, Role
from apps.visit_guide.models import GuideSection, GuideStatus
from apps.visit_guide.services import (
    StaleRulesError,
    acknowledge_rules,
    create_section,
    publish_section,
    unpublish_section,
    update_section,
)
from config.api import api

operator_router = Router(auth=operator_required, tags=["operator-visit-guide"])
public_router = Router(tags=["visit-guide"])
fan_router = Router(auth=[FanBearerAuth()], tags=["fan-visit-guide"])

_TITLE_MAX = 200
_BODY_MAX = 8000


class GuideError(Schema):
    """Stable error shape for visit-guide endpoints."""

    detail: str


class SectionOut(Schema):
    """Section fields exposed to operator tools (all statuses)."""

    id: uuid.UUID
    section_type: str
    title: str
    body: str
    version: int
    status: str
    display_order: int
    store_id: str
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class PublicSectionOut(Schema):
    """Published-section fields exposed publicly (no operator-only data)."""

    id: uuid.UUID
    section_type: str
    title: str
    body: str
    version: int
    display_order: int


class SectionCreateIn(Schema):
    """Operator payload to create a draft section."""

    section_type: str
    title: str = Field(max_length=_TITLE_MAX)
    body: str = Field(default="", max_length=_BODY_MAX)
    display_order: int = Field(default=0, ge=0)


class SectionUpdateIn(Schema):
    """Operator change to a draft section; omitted fields are unchanged."""

    title: str | None = Field(default=None, max_length=_TITLE_MAX)
    body: str | None = Field(default=None, max_length=_BODY_MAX)
    display_order: int | None = Field(default=None, ge=0)


class AckIn(Schema):
    """Fan payload to acknowledge the rules: the version the fan actually read."""

    version: int = Field(ge=0)


class AckOut(Schema):
    """Result of acknowledging the usage rules."""

    acknowledged: bool
    version: int


# --------------------------------------------------------------------------- #
# Operator surface
# --------------------------------------------------------------------------- #
@operator_router.post("", response={201: SectionOut, 400: GuideError})
def operator_create_section(
    request: HttpRequest, payload: SectionCreateIn
) -> tuple[int, SectionOut | GuideError]:
    """Create a draft guide section."""
    try:
        section = create_section(
            actor=_actor(request),
            section_type=payload.section_type,
            title=payload.title,
            body=payload.body,
            display_order=payload.display_order,
        )
    except ValueError as exc:
        return 400, GuideError(detail=str(exc))
    return 201, _section_out(section)


@operator_router.get("", response=list[SectionOut])
def operator_list_sections(
    request: HttpRequest, status: str | None = None, section_type: str | None = None
) -> list[SectionOut]:
    """List guide sections (all statuses), optionally filtered."""
    del request
    qs = GuideSection.objects.all()
    if status:
        qs = qs.filter(status=status)
    if section_type:
        qs = qs.filter(section_type=section_type)
    return [_section_out(s) for s in qs]


@operator_router.get("/{section_id}", response={200: SectionOut, 404: GuideError})
def operator_get_section(
    request: HttpRequest, section_id: uuid.UUID
) -> tuple[int, SectionOut | GuideError]:
    """Read one section (any status)."""
    del request
    section = get_object_or_404(GuideSection, id=section_id)
    return 200, _section_out(section)


@operator_router.post(
    "/{section_id}/update", response={200: SectionOut, 400: GuideError, 404: GuideError}
)
def operator_update_section(
    request: HttpRequest, section_id: uuid.UUID, payload: SectionUpdateIn
) -> tuple[int, SectionOut | GuideError]:
    """Edit a draft section."""
    section = get_object_or_404(GuideSection, id=section_id)
    try:
        updated = update_section(
            section=section,
            actor=_actor(request),
            title=payload.title,
            body=payload.body,
            display_order=payload.display_order,
        )
    except ValueError as exc:
        return 400, GuideError(detail=str(exc))
    return 200, _section_out(updated)


@operator_router.post(
    "/{section_id}/publish", response={200: SectionOut, 400: GuideError, 404: GuideError}
)
def operator_publish_section(
    request: HttpRequest, section_id: uuid.UUID
) -> tuple[int, SectionOut | GuideError]:
    """Publish a draft section (now public)."""
    section = get_object_or_404(GuideSection, id=section_id)
    try:
        published = publish_section(section=section, actor=_actor(request))
    except ValueError as exc:
        return 400, GuideError(detail=str(exc))
    return 200, _section_out(published)


@operator_router.post(
    "/{section_id}/unpublish", response={200: SectionOut, 400: GuideError, 404: GuideError}
)
def operator_unpublish_section(
    request: HttpRequest, section_id: uuid.UUID
) -> tuple[int, SectionOut | GuideError]:
    """Return a published section to draft (비공개)."""
    section = get_object_or_404(GuideSection, id=section_id)
    try:
        drafted = unpublish_section(section=section, actor=_actor(request))
    except ValueError as exc:
        return 400, GuideError(detail=str(exc))
    return 200, _section_out(drafted)


# --------------------------------------------------------------------------- #
# Public surface — published guide (unauthenticated, pre-visit reading)
# --------------------------------------------------------------------------- #
@public_router.get("", response=list[PublicSectionOut])
def public_list_sections(request: HttpRequest) -> list[PublicSectionOut]:
    """List published guide sections (drafts are never shown)."""
    del request
    rows = GuideSection.objects.filter(status=GuideStatus.PUBLISHED.value)
    return [_public_out(s) for s in rows]


@public_router.get("/{section_id}", response={200: PublicSectionOut, 404: GuideError})
def public_get_section(
    request: HttpRequest, section_id: uuid.UUID
) -> tuple[int, PublicSectionOut | GuideError]:
    """Read one published section; a draft id is a 404 (no existence leak)."""
    del request
    section = get_object_or_404(GuideSection, id=section_id, status=GuideStatus.PUBLISHED.value)
    return 200, _public_out(section)


# --------------------------------------------------------------------------- #
# Fan surface — rule acknowledgement (bearer only; role-gated)
# --------------------------------------------------------------------------- #
@fan_router.post(
    "/acknowledge-rules",
    response={200: AckOut, 400: GuideError, 403: GuideError, 409: GuideError},
)
def fan_acknowledge_rules(request: HttpRequest, payload: AckIn) -> tuple[int, AckOut | GuideError]:
    """Record the fan's consent to the usage-rules version they read.

    The fan sends the ``version`` they saw (from the public read); a republish in
    the meantime makes it stale → 409 so the client reloads (consent is never
    recorded for a version the fan did not see).
    """
    fan = _actor(request)
    if fan.role != Role.FAN.value:
        return 403, GuideError(detail="Only fans can acknowledge the rules.")
    try:
        version = acknowledge_rules(fan=fan, expected_version=payload.version)
    except StaleRulesError as exc:
        return 409, GuideError(detail=str(exc))
    except ValueError as exc:
        return 400, GuideError(detail=str(exc))
    return 200, AckOut(acknowledged=True, version=version)


def _actor(request: HttpRequest) -> Account:
    """Return the authenticated account supplied by the auth class."""
    # request.auth is untyped without Ninja stubs (same idiom as visit/api.py).
    return cast(Account, request.auth)  # type: ignore[attr-defined]


def _section_out(section: GuideSection) -> SectionOut:
    """Build the operator response schema for a section."""
    return SectionOut(
        id=section.id,
        section_type=section.section_type,
        title=section.title,
        body=section.body,
        version=section.version,
        status=section.status,
        display_order=section.display_order,
        store_id=section.store_id,
        created_by_id=section.created_by_id,
        created_at=section.created_at,
        updated_at=section.updated_at,
    )


def _public_out(section: GuideSection) -> PublicSectionOut:
    """Build the public response schema (no operator-only fields)."""
    return PublicSectionOut(
        id=section.id,
        section_type=section.section_type,
        title=section.title,
        body=section.body,
        version=section.version,
        display_order=section.display_order,
    )


api.add_router("/operator/visit-guide", operator_router)
api.add_router("/visit-guide", public_router)
api.add_router("/fan/visit-guide", fan_router)
