"""Audit trail for privileged actions (ASS-91, CONSTRAINTS HITL #26).

Every permission change, block, invalidation, and data export must leave an
``AuditEntry`` (architecture: admin owns audit). The trail is the accountability
record reviewers and operators rely on, so it captures *who* did *what* to
*which* target and *why*. Like the event log it is meant to be append-only in
spirit; mutation helpers are deliberately not provided.
"""

from __future__ import annotations

from django.db import models


class AuditAction(models.TextChoices):
    """Privileged action categories that must be audited.

    Kept as an enum so callers cannot record free-form action strings that would
    fragment the trail and defeat later querying.
    """

    ROLE_CHANGED = "role_changed", "role_changed"
    USER_BLOCKED = "user_blocked", "user_blocked"
    USER_UNBLOCKED = "user_unblocked", "user_unblocked"
    RECORD_INVALIDATED = "record_invalidated", "record_invalidated"
    DATA_EXPORTED = "data_exported", "data_exported"
    SAFETY_DETAIL_VIEWED = "safety_detail_viewed", "safety_detail_viewed"
    DASHBOARD_VIEWED = "dashboard_viewed", "dashboard_viewed"
    VISIT_RECORDED = "visit_recorded", "visit_recorded"
    VISIT_CORRECTED = "visit_corrected", "visit_corrected"
    VISIT_VOIDED = "visit_voided", "visit_voided"
    CHEKI_RECORDED = "cheki_recorded", "cheki_recorded"
    CHEKI_CORRECTED = "cheki_corrected", "cheki_corrected"
    CHEKI_VOIDED = "cheki_voided", "cheki_voided"
    SAFETY_REPORT_CREATED = "safety_report_created", "safety_report_created"
    SAFETY_REPORT_STATUS_CHANGED = (
        "safety_report_status_changed",
        "safety_report_status_changed",
    )
    SAFETY_REPORT_RESOLVED = "safety_report_resolved", "safety_report_resolved"
    USER_RISK_FLAGGED = "user_risk_flagged", "user_risk_flagged"
    SCHEDULE_CREATED = "schedule_created", "schedule_created"
    SCHEDULE_EDITED = "schedule_edited", "schedule_edited"
    SCHEDULE_PUBLISHED = "schedule_published", "schedule_published"
    SCHEDULE_UNPUBLISHED = "schedule_unpublished", "schedule_unpublished"
    SCHEDULE_CHANGE_REQUESTED = (
        "schedule_change_requested",
        "schedule_change_requested",
    )
    SCHEDULE_CHANGE_APPROVED = (
        "schedule_change_approved",
        "schedule_change_approved",
    )
    SCHEDULE_CHANGE_REJECTED = (
        "schedule_change_rejected",
        "schedule_change_rejected",
    )
    CAST_PROFILE_CREATED = "cast_profile_created", "cast_profile_created"
    CAST_PROFILE_UPDATED = "cast_profile_updated", "cast_profile_updated"
    CAST_CONSENT_RECORDED = "cast_consent_recorded", "cast_consent_recorded"


class AuditEntry(models.Model):
    """One recorded privileged action.

    ``actor`` is the staff account that acted; ``target`` is a free-form
    identifier of the affected subject (account id, record id, export name) since
    targets span many models. ``reason`` is mandatory for exports and safety
    access per compliance, so it is captured here rather than inferred.
    """

    actor = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=32, choices=AuditAction.choices)
    target = models.CharField(max_length=255)
    reason = models.CharField(max_length=512, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Summarise the audited action for log/admin display."""
        return f"{self.action} by {self.actor_id} -> {self.target}"
