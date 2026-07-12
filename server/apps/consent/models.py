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


class MarketingChannel(models.TextChoices):
    """The channels a fan can opt into for marketing messages (D8, 2026-07-12).

    Marketing consent is per-channel (채널별 분리) and optional — refusing any/all
    never blocks service use. ``email`` is listed for forward compatibility even
    though email is not collected yet (the settings UI shows it disabled).
    """

    PUSH = "push", "push"
    SMS = "sms", "sms"
    EMAIL = "email", "email"


class MarketingConsent(models.Model):
    """A fan's current opt-in state for one marketing channel (D8).

    Unlike the append-only :class:`ConsentRecord` audit trail, this is the *current*
    state the send-time gate reads: one upserted row per (account, channel) holding
    the live ``enabled`` flag. Each change also appends a ``ConsentRecord`` (kind
    ``marketing``, version ``marketing:<channel>:<on|off>``) so the grant/withdraw
    history stays durable. Absence of a row means not opted in (fail-closed).
    """

    account = models.ForeignKey(
        "identity.Account",
        on_delete=models.CASCADE,
        related_name="marketing_consents",
    )
    channel = models.CharField(max_length=16, choices=MarketingChannel.choices)
    enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "channel"], name="uniq_marketing_channel"
            ),
        ]

    def __str__(self) -> str:
        """Summarise the channel state for admin/log display."""
        state = "on" if self.enabled else "off"
        return f"marketing:{self.account_id}:{self.channel}={state}"
