"""Domain models for the visit guide / 이용 안내 CMS (F02, ASS-101 v0).

Operators author the pre-visit guidance a first-time customer reads (usage rules,
first-visit guide, operating hours, what a cheki means, photography policy,
prohibited actions, and the platform principles). Each section is created as a
draft and **published** — publication is the fail-closed approval gate, so
unapproved copy never reaches the public surface, mirroring the event_campaign
"승인 전 비공개" gate (ASS-107).

Out of scope for v0 (held — the issue Blocker): the **price / menu actual
values**. 가격·메뉴 실제 값은 승인 필요(Development_Constraints / CONSTRAINTS L91):
the model stores **no money figure** and provides no pricing/menu section, so an
unapproved price can never be published here. The approved price values are a
separate, approval-gated deferred slice.

A fan acknowledges the published usage-rules version via the consent app
(``rule_consent_given``), so the rule consent is recorded against the exact
version the fan saw; republishing the rules bumps the version and invalidates the
old acknowledgement.
"""

from __future__ import annotations

import uuid

from django.db import models

# Single café for Release 0.1 (mirrors visit.models.DEFAULT_STORE_ID rationale).
DEFAULT_STORE_ID = "hatsukoi"


class GuideSectionType(models.TextChoices):
    """The pre-visit guidance sections (no pricing/menu values — those are held)."""

    USAGE_RULES = "usage_rules", "이용 규칙"
    FIRST_VISIT_GUIDE = "first_visit_guide", "첫 방문 가이드"
    OPERATING_HOURS = "operating_hours", "이용 시간"
    CHEKI_MEANING = "cheki_meaning", "체키 의미"
    PHOTO_POLICY = "photo_policy", "촬영 범위"
    PROHIBITED_ACTIONS = "prohibited_actions", "금지 행동"
    PRINCIPLES = "principles", "이용 원칙"


class GuideStatus(models.TextChoices):
    """Lifecycle. Draft is non-public (승인 전 비공개); published is fan-visible."""

    DRAFT = "draft", "draft"
    PUBLISHED = "published", "published"


class GuideSection(models.Model):
    """One operator-authored guide section (F02).

    Exactly one row per ``(store_id, section_type)``; operators edit it as a draft
    and publish it. Public only while ``status=published``. ``version`` increments
    on each publication so the rule-consent acknowledgement can be tied to the
    exact published version a fan saw. No money figure is stored (가격 값은 승인
    게이트 뒤 보류).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section_type = models.CharField(max_length=32, choices=GuideSectionType.choices)
    title = models.CharField(max_length=200)
    # Operator-authored guidance text. No price/menu figure (the value is the
    # approval-gated, deferred slice); publication is the approval gate for copy.
    body = models.TextField(blank=True, default="")
    # Publication counter: 0 = never published; +1 on each publish. The usage-rules
    # acknowledgement records this version so a republish invalidates old consent.
    version = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=GuideStatus.choices, default=GuideStatus.DRAFT)
    display_order = models.PositiveIntegerField(default=0)
    store_id = models.CharField(max_length=64, default=DEFAULT_STORE_ID)
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_guide_sections",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # One section per type per store: the guide has a single canonical
            # rules / first-visit / … section that operators edit in place.
            models.UniqueConstraint(
                fields=["store_id", "section_type"],
                name="uniq_guide_section_per_type",
            ),
        ]
        indexes = [
            models.Index(fields=["store_id", "status"]),
            models.Index(fields=["status", "display_order"]),
        ]
        ordering = ["display_order", "section_type"]

    def __str__(self) -> str:
        """Summarise the section for log/admin display (no personal data)."""
        return f"{self.section_type} {self.id} ({self.status})"
