"""Domain models for safety reports and user blocks (ASS-96, F11).

Safety comes before fandom features (Company-OS 제약 #3). This app records the
*operator* side: a report's classification + status, the sensitive narrative in a
**separate restricted table**, and user blocks. Two hard rules shape the design:

1. The narrative / reporter contact / any PII lives ONLY in
   :class:`SafetyReportDetail` (the restricted store), never on the summary row
   and never in an event (``FORBIDDEN_SAFETY_PROPERTY_KEYS`` enforces the event
   side). Field-level access is gated to manager+ via ``admin_rbac.redaction``.
2. Reports and blocks are never deleted — only their ``status`` changes — so the
   audit trail and reconciliation stay intact (Data 제약).

Field names mirror ``admin_rbac.redaction`` (summary vs detail sets) so the
redaction transform lines up with what the API serialises.
"""

from __future__ import annotations

import uuid

from django.db import models


class ReportType(models.TextChoices):
    """Canonical report categories (Data_Event_Schema safety_report_created)."""

    UNWANTED_REQUEST = "unwanted_request", "unwanted_request"
    PRIVATE_CONTACT = "private_contact", "private_contact"
    EXTERNAL_MEETING = "external_meeting", "external_meeting"
    VERBAL_ABUSE = "verbal_abuse", "verbal_abuse"
    PHYSICAL_THREAT = "physical_threat", "physical_threat"
    PHOTO_VIOLATION = "photo_violation", "photo_violation"
    STALKING_CONCERN = "stalking_concern", "stalking_concern"
    REFUND_DISPUTE = "refund_dispute", "refund_dispute"
    PRIVACY_PORTRAIT_CONCERN = (
        "privacy_portrait_concern",
        "privacy_portrait_concern",
    )
    FRAUD_ABUSE = "fraud_abuse", "fraud_abuse"
    OTHER = "other", "other"


class ReportSeverity(models.TextChoices):
    """Severity; high/critical force manager_only visibility."""

    LOW = "low", "low"
    MEDIUM = "medium", "medium"
    HIGH = "high", "high"
    CRITICAL = "critical", "critical"


class ReportStatus(models.TextChoices):
    """Handling lifecycle: 접수→검토→조치→종료."""

    RECEIVED = "received", "received"
    REVIEWING = "reviewing", "reviewing"
    ACTIONED = "actioned", "actioned"
    CLOSED = "closed", "closed"


class ReportVisibility(models.TextChoices):
    """Who may see the detail fields (admin_rbac.redaction gates on this)."""

    RESTRICTED = "restricted", "restricted"
    MANAGER_ONLY = "manager_only", "manager_only"


class ActorKind(models.TextChoices):
    """reporter_type / target_type domains (Data_Event_Schema)."""

    FAN = "fan", "fan"
    CAST = "cast", "cast"
    OPERATOR = "operator", "operator"
    ADMIN = "admin", "admin"
    UNKNOWN = "unknown", "unknown"


class SafetyReport(models.Model):
    """Summary + classification row for a safety report (operator-visible).

    Carries no narrative or PII — only the classification, status, and visibility
    an operator may triage on. The sensitive content is in the one-to-one
    :class:`SafetyReportDetail`, reachable only by manager+.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=32, choices=ReportType.choices)
    severity = models.CharField(max_length=16, choices=ReportSeverity.choices)
    status = models.CharField(
        max_length=16,
        choices=ReportStatus.choices,
        default=ReportStatus.RECEIVED,
    )
    visibility = models.CharField(
        max_length=16,
        choices=ReportVisibility.choices,
        default=ReportVisibility.RESTRICTED,
    )
    reporter_type = models.CharField(max_length=16, choices=ActorKind.choices)
    target_type = models.CharField(max_length=16, choices=ActorKind.choices)
    # reporter/target are detail fields (manager-gated in serialisation). Either
    # may be unknown/non-fan, so both FKs are nullable and a cast is a string id
    # (no Cast model yet). PROTECT preserves the accountability link.
    reporter = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="filed_safety_reports",
        null=True,
        blank=True,
    )
    target = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="targeted_safety_reports",
        null=True,
        blank=True,
    )
    cast_id = models.CharField(max_length=64, blank=True, default="")
    visit = models.ForeignKey(
        "visit.VisitRecord",
        on_delete=models.PROTECT,
        related_name="safety_reports",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_safety_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["severity", "status"]),
            models.Index(fields=["report_type"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the report by type/severity/status (no PII)."""
        return f"report:{self.id}:{self.report_type}/{self.severity}/{self.status}"


class SafetyReportDetail(models.Model):
    """The restricted store: narrative + resolution notes, manager+ only.

    Kept in a separate table (not on :class:`SafetyReport`) so operator-facing
    queries never select the sensitive text, and access can be gated at the row
    level. ``narrative`` is the reporter's account; it must never be copied into
    an event payload.
    """

    report = models.OneToOneField(
        SafetyReport,
        on_delete=models.PROTECT,
        related_name="detail",
        primary_key=True,
    )
    narrative = models.TextField(blank=True, default="")
    resolution_note = models.TextField(blank=True, default="")
    manager_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Identify the detail by its report id (never echo the narrative)."""
        return f"report-detail:{self.report_id}"


class BlockScope(models.TextChoices):
    """What a block restricts (Data_Event_Schema block_scope domain)."""

    RESERVATION = "reservation", "reservation"
    FANDOM_FEATURE = "fandom_feature", "fandom_feature"
    STORE_VISIT = "store_visit", "store_visit"
    ALL = "all", "all"


class BlockReason(models.TextChoices):
    """Closed reason codes (Data_Event_Schema user_blocked block_reason).

    A closed enum — never free text — so the ``user_blocked`` event and audit
    cannot carry a narrative or PII (the value-level leak a free string allows).
    """

    POLICY_VIOLATION = "policy_violation", "policy_violation"
    SAFETY_RISK = "safety_risk", "safety_risk"
    HARASSMENT = "harassment", "harassment"
    FRAUD = "fraud", "fraud"
    DISPUTE = "dispute", "dispute"
    OTHER = "other", "other"


class BlockStatus(models.TextChoices):
    """Block lifecycle — lifted, never deleted."""

    ACTIVE = "active", "active"
    LIFTED = "lifted", "lifted"


class UserBlock(models.Model):
    """A block/limit on a fan, enforced by feature surfaces (reservation, etc.).

    Blocks are status-changed (active→lifted), never deleted, so the history of
    why a fan was limited survives. ``is_risk_flag`` marks the lighter "위험 고객"
    annotation that limits without a hard block.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="blocks",
    )
    block_scope = models.CharField(max_length=16, choices=BlockScope.choices)
    block_reason = models.CharField(max_length=255)
    is_risk_flag = models.BooleanField(default=False)
    effective_from = models.DateTimeField()
    status = models.CharField(
        max_length=16,
        choices=BlockStatus.choices,
        default=BlockStatus.ACTIVE,
    )
    lifted_reason = models.TextField(blank=True, default="")
    source_report = models.ForeignKey(
        SafetyReport,
        on_delete=models.PROTECT,
        related_name="blocks",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_blocks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["target", "status"]),
            models.Index(fields=["status", "effective_from"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the block by target/scope/status."""
        return f"block:{self.id}:{self.target_id}/{self.block_scope}/{self.status}"
