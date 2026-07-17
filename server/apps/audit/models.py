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
    POS_ORDER_LINKED = "pos_order_linked", "pos_order_linked"
    POS_ORDER_VOIDED = "pos_order_voided", "pos_order_voided"
    RESERVATION_CREATED = "reservation_created", "reservation_created"
    RESERVATION_CONFIRMED = "reservation_confirmed", "reservation_confirmed"
    RESERVATION_CHANGED = "reservation_changed", "reservation_changed"
    RESERVATION_CANCELLED = "reservation_cancelled", "reservation_cancelled"
    RESERVATION_NO_SHOW = "reservation_no_show", "reservation_no_show"
    EVENT_CAMPAIGN_CREATED = "event_campaign_created", "event_campaign_created"
    EVENT_CAMPAIGN_UPDATED = "event_campaign_updated", "event_campaign_updated"
    EVENT_CAMPAIGN_PUBLISHED = "event_campaign_published", "event_campaign_published"
    EVENT_CAMPAIGN_UNPUBLISHED = (
        "event_campaign_unpublished",
        "event_campaign_unpublished",
    )
    EVENT_CAMPAIGN_CLOSED = "event_campaign_closed", "event_campaign_closed"
    GUIDE_SECTION_CREATED = "guide_section_created", "guide_section_created"
    GUIDE_SECTION_UPDATED = "guide_section_updated", "guide_section_updated"
    GUIDE_SECTION_PUBLISHED = "guide_section_published", "guide_section_published"
    GUIDE_SECTION_UNPUBLISHED = "guide_section_unpublished", "guide_section_unpublished"
    COUPON_ISSUED = "coupon_issued", "coupon_issued"
    COUPON_REDEEMED = "coupon_redeemed", "coupon_redeemed"
    COUPON_CANCELLED = "coupon_cancelled", "coupon_cancelled"
    COUPON_EXPIRED = "coupon_expired", "coupon_expired"
    POINT_GRANTED = "point_granted", "point_granted"
    POINT_ADJUSTED = "point_adjusted", "point_adjusted"
    # Operator-driven refund review (commerce, R6-W1A). A refund request moves
    # requested→reviewing (REVIEWED), reviewing/requested→accepted (ACCEPTED, which
    # also cancels+restocks the order), or →rejected (REJECTED). Money never moves
    # (mock order flow, B7-gated) — these audit the operator's decision, not a
    # settlement.
    REFUND_REVIEWED = "refund_reviewed", "refund_reviewed"
    REFUND_ACCEPTED = "refund_accepted", "refund_accepted"
    REFUND_REJECTED = "refund_rejected", "refund_rejected"
    # Report-driven media moderation (대표 approved 07-18): an operator took a safety
    # report about an uploaded image to ``actioned``, so the image stopped being
    # served. A dedicated action (rather than only the report's status-change entry)
    # so "when/why did this image stop resolving" is directly queryable.
    UPLOAD_TAKEN_DOWN = "upload_taken_down", "upload_taken_down"
    # The inverse: an operator moved an actioned report about an image back off
    # ``actioned``, so the image was un-quarantined and serves again. Recorded
    # separately from the takedown (never as its absence) because a mis-click that
    # removed a creator's image and the reversal of it are both accountable acts.
    UPLOAD_RESTORED = "upload_restored", "upload_restored"


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
