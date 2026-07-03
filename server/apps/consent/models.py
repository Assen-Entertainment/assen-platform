"""Consent records and the business-command consent gate.

Compliance (CONSTRAINTS #8/#9) requires recorded, versioned consent before a fan
performs meaningful business actions. ``ConsentRecord`` captures each grant;
:func:`apps.consent.gate.require_consent` blocks commands for accounts missing a
required consent kind. The final legal wording is human-approved (architecture:
consent module — 최종 문구는 승인 필요), so this layer models the *mechanism*, not
the copy.
"""

from __future__ import annotations

from django.db import models


class ConsentKind(models.TextChoices):
    """The consent categories tracked at P0 (rule/privacy/terms + marketing).

    ``rule`` corresponds to the ``rule_consent_given`` P0_required event
    (price/usage rules); privacy and terms are mandatory for signup; marketing is
    optional.
    """

    RULE = "rule", "rule"
    PRIVACY = "privacy", "privacy"
    TERMS = "terms", "terms"
    MARKETING = "marketing", "marketing"
    # 성인(19+) 연령 확인 동의. 본인인증(KYC) 확정 시 기록되며, age-gate 프론트가
    # "age"를 사용하므로 record_consent의 enum 검증을 통과하려면 필수. 저장되는 것은
    # 동의 사실(kind/version)뿐 — 생년월일 원본은 저장하지 않는다(법무 경계 §2).
    AGE = "age", "age"


class ConsentRecord(models.Model):
    """A single consent grant by an account for one kind at one version.

    Versioned because consent must be re-collected when the wording materially
    changes; storing the version lets the gate require the *current* version, not
    merely "ever consented".
    """

    account = models.ForeignKey(
        "identity.Account",
        on_delete=models.CASCADE,
        related_name="consent_records",
    )
    kind = models.CharField(max_length=16, choices=ConsentKind.choices)
    version = models.CharField(max_length=32)
    given_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["account", "kind"])]
        ordering = ["-given_at"]

    def __str__(self) -> str:
        """Summarise the grant for admin/log display."""
        return f"consent:{self.account_id}:{self.kind}@{self.version}"
