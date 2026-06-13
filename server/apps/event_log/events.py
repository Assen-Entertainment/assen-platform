"""Canonical event registry: names, common-field enums, and per-event schemas.

Single source of truth for event naming is Company-OS
`02_Product/Data_Event_Schema.md`. This module mirrors that contract in code so
the validation layer fails fast on drift instead of silently storing malformed
events. Names are past-tense ``object_action`` snake_case and never change when a
POS vendor changes (vendor-specific names belong in ``properties.vendor_event_name``).

Why a registry rather than free-form strings: every persisted ``EventRecord`` is
analytics input (MSFC, 30-day revisit). An unknown event name or a missing
required field would corrupt those metrics, so emission validates against the
schema declared here before the row is ever written.
"""

from __future__ import annotations

from django.db import models
from pydantic import BaseModel, ConfigDict


class EventName(models.TextChoices):
    """The P0 event names this platform records.

    Sourced from ASS-90's core-20 list, reconciled against Data_Event_Schema.md
    canonical names, plus the reservation pair (``reservation_created`` /
    ``reservation_cancelled``) which Data_Event_Schema marks P0_required (F03,
    ASS-84 reconciliation) and the staged-identity / consent events those flows
    must emit (``anonymous_user_created``, ``anonymous_user_merged``,
    ``rule_consent_given``). Membership in this enum is enforced at emit time.
    """

    # Fan / signup / identity / consent.
    FAN_SIGNED_UP = "fan_signed_up", "fan_signed_up"
    ANONYMOUS_USER_CREATED = "anonymous_user_created", "anonymous_user_created"
    ANONYMOUS_USER_MERGED = "anonymous_user_merged", "anonymous_user_merged"
    RULE_CONSENT_GIVEN = "rule_consent_given", "rule_consent_given"

    # Reservation (F03 — P0_required in Data_Event_Schema, added per ASS-84).
    RESERVATION_CREATED = "reservation_created", "reservation_created"
    RESERVATION_CANCELLED = "reservation_cancelled", "reservation_cancelled"

    # Visit.
    VISIT_CHECKED_IN = "visit_checked_in", "visit_checked_in"
    VISIT_COMPLETED = "visit_completed", "visit_completed"
    # ``visit_invalidated`` is P0_required in Data_Event_Schema (L274, 방문 기록
    # 무효 → MSFC 제외) but was missing from ASS-90's enum; registered here so an
    # operator void (ASS-94) emits the canonical exclusion event through the
    # validated ``emit_event`` funnel rather than a bespoke name.
    VISIT_INVALIDATED = "visit_invalidated", "visit_invalidated"

    # Cast / schedule / favorite.
    CAST_PROFILE_VIEWED = "cast_profile_viewed", "cast_profile_viewed"
    SCHEDULE_VIEWED = "schedule_viewed", "schedule_viewed"
    FAVORITE_ADDED = "favorite_added", "favorite_added"
    FAVORITE_REMOVED = "favorite_removed", "favorite_removed"

    # Cheki.
    CHEKI_RECORDED = "cheki_recorded", "cheki_recorded"

    # Event / campaign.
    EVENT_VIEWED = "event_viewed", "event_viewed"
    EVENT_RESERVED = "event_reserved", "event_reserved"

    # Coupon.
    COUPON_ISSUED = "coupon_issued", "coupon_issued"
    COUPON_REDEEMED = "coupon_redeemed", "coupon_redeemed"

    # POS.
    POS_ORDER_LINKED = "pos_order_linked", "pos_order_linked"
    POS_RECONCILIATION_FLAGGED = "pos_reconciliation_flagged", "pos_reconciliation_flagged"
    PAYMENT_REFUNDED = "payment_refunded", "payment_refunded"

    # Safety.
    SAFETY_REPORT_CREATED = "safety_report_created", "safety_report_created"
    SAFETY_REPORT_RESOLVED = "safety_report_resolved", "safety_report_resolved"
    USER_BLOCKED = "user_blocked", "user_blocked"

    # Admin.
    ADMIN_NOTE_CREATED = "admin_note_created", "admin_note_created"


class ActorType(models.TextChoices):
    """Who performed the action (Data_Event_Schema common field ``actor_type``).

    ``operator``/``admin``/``system`` actors are non-fan; metrics exclude them
    (see ``EventRecord.actor_is_operator``).
    """

    FAN = "fan", "fan"
    CAST = "cast", "cast"
    OPERATOR = "operator", "operator"
    ADMIN = "admin", "admin"
    SYSTEM = "system", "system"


class EventSource(models.TextChoices):
    """Origin surface of the event (Data_Event_Schema common field ``source``)."""

    FAN_APP = "fan_app", "fan_app"
    WEB = "web", "web"
    ADMIN = "admin", "admin"
    KIOSK = "kiosk", "kiosk"
    MANUAL = "manual", "manual"
    POS_CSV = "pos_csv", "pos_csv"
    POS_API = "pos_api", "pos_api"
    POS_WEBHOOK = "pos_webhook", "pos_webhook"
    SYSTEM = "system", "system"


class EventStatus(models.TextChoices):
    """Lifecycle status (Data_Event_Schema 상태값 표준, general status set)."""

    PENDING = "pending", "pending"
    COMPLETED = "completed", "completed"
    CANCELLED = "cancelled", "cancelled"
    REFUNDED = "refunded", "refunded"
    INVALIDATED = "invalidated", "invalidated"
    RESOLVED = "resolved", "resolved"


# Field keys that must never appear inside a safety event's ``properties`` blob.
# Data_Event_Schema 개인정보 기준 ("신고 상세 원문 전문을 일반 이벤트 속성에 저장"
# 금지): raw report narrative lives in a restricted store, the event keeps only
# type/severity/status/ids. We block the common keys a caller might use to smuggle
# the narrative in, so the separation is enforced rather than merely documented.
FORBIDDEN_SAFETY_PROPERTY_KEYS: frozenset[str] = frozenset(
    {
        "report_text",
        "report_body",
        "report_detail",
        "report_details",
        "narrative",
        "raw_report",
        "raw_text",
        "detail_text",
        "description",
        "message",
        "contact",
        "phone",
        "id_image",
        "card_number",
    }
)

# Safety events whose properties are scrubbed against the forbidden-key list.
SAFETY_EVENT_NAMES: frozenset[str] = frozenset(
    {
        EventName.SAFETY_REPORT_CREATED.value,
        EventName.SAFETY_REPORT_RESOLVED.value,
        EventName.USER_BLOCKED.value,
    }
)


class _PayloadModel(BaseModel):
    """Base for per-event payload schemas.

    ``extra="allow"`` keeps the schema forward-compatible: events legitimately
    carry optional context beyond the required keys, and we validate only that
    the required keys are present and typed, not that the payload is closed.
    """

    model_config = ConfigDict(extra="allow")


class FanSignedUpPayload(_PayloadModel):
    """``fan_signed_up`` required properties (Data_Event_Schema L359-372)."""

    fan_id: str
    signup_method: str
    consent_terms: bool
    consent_privacy: bool


class AnonymousUserCreatedPayload(_PayloadModel):
    """``anonymous_user_created`` — temporary identity for pre-signup activity."""

    anonymous_id: str


class AnonymousUserMergedPayload(_PayloadModel):
    """``anonymous_user_merged`` — links a temp identity to a fan_id.

    Carries both ids so MSFC re-attribution can fold pre-merge anonymous events
    into the fan without deleting history (Data_Event_Schema L764-769).
    """

    anonymous_id: str
    fan_id: str


class RuleConsentGivenPayload(_PayloadModel):
    """``rule_consent_given`` — price/usage rule consent (gate prerequisite)."""

    fan_id: str
    consent_kind: str
    consent_version: str


class ReservationCreatedPayload(_PayloadModel):
    """``reservation_created`` required properties (F03, P0_required)."""

    fan_id: str
    reservation_id: str


class ReservationCancelledPayload(_PayloadModel):
    """``reservation_cancelled`` required properties (F03, P0_required)."""

    fan_id: str
    reservation_id: str


class VisitCheckedInPayload(_PayloadModel):
    """``visit_checked_in`` required properties (Data_Event_Schema L378-394).

    ``visit_type``/``checkin_method``/``is_verified_offline_visit`` drive the
    MSFC start condition (verified_offline_visit). ``fan_id`` is conditional:
    anonymous check-ins carry ``anonymous_id`` instead and are excluded from MSFC
    until merged.
    """

    visit_id: str
    store_id: str
    business_day: str
    visit_type: str
    checkin_method: str
    is_verified_offline_visit: bool


class VisitCompletedPayload(_PayloadModel):
    """``visit_completed`` required properties (Data_Event_Schema L401-413)."""

    fan_id: str
    visit_id: str
    completed_at: str
    has_payment_reference: bool


class VisitInvalidatedPayload(_PayloadModel):
    """``visit_invalidated`` required properties (Data_Event_Schema L274).

    A corrective, append-only event: the original ``visit_checked_in`` row is
    never mutated, so invalidation is expressed as this new event carrying the
    ``visit_id`` analytics must exclude. ``reason`` is the operator's void reason
    for the operational trail; it carries no personal data.
    """

    visit_id: str
    reason: str


class CastProfileViewedPayload(_PayloadModel):
    """``cast_profile_viewed`` — cast profile impression."""

    cast_id: str


class ScheduleViewedPayload(_PayloadModel):
    """``schedule_viewed`` required properties (Data_Event_Schema L419-438)."""

    store_id: str
    business_day: str
    viewed_for_date: str
    view_scope: str
    source_surface: str


class FavoriteAddedPayload(_PayloadModel):
    """``favorite_added`` required properties (Data_Event_Schema L444-455)."""

    fan_id: str
    cast_id: str
    favorite_source: str


class FavoriteRemovedPayload(_PayloadModel):
    """``favorite_removed`` — fan removes a cast from favorites."""

    fan_id: str
    cast_id: str


class ChekiRecordedPayload(_PayloadModel):
    """``cheki_recorded`` required properties (Data_Event_Schema L461-479)."""

    visit_id: str
    cast_id: str
    cheki_id: str
    cheki_type: str
    quantity: int
    image_stored: bool


class EventViewedPayload(_PayloadModel):
    """``event_viewed`` — campaign/event impression."""

    event_campaign_id: str


class EventReservedPayload(_PayloadModel):
    """``event_reserved`` required properties (Data_Event_Schema L485-498)."""

    fan_id: str
    event_campaign_id: str
    reservation_id: str
    event_type: str
    reservation_status: str


class CouponIssuedPayload(_PayloadModel):
    """``coupon_issued`` — coupon granted to a fan."""

    fan_id: str
    coupon_id: str
    coupon_type: str


class CouponRedeemedPayload(_PayloadModel):
    """``coupon_redeemed`` required properties (Data_Event_Schema L504-520)."""

    fan_id: str
    coupon_id: str
    coupon_redemption_id: str
    coupon_type: str
    redemption_status: str


class PosOrderLinkedPayload(_PayloadModel):
    """``pos_order_linked`` required properties (Data_Event_Schema L526-542)."""

    visit_id: str
    link_method: str
    payment_status: str
    linked_confidence: str


class PosReconciliationFlaggedPayload(_PayloadModel):
    """``pos_reconciliation_flagged`` — daily POS reconciliation mismatch found.

    P0 operational-quality event carried in ASS-90's core list (matches
    Data_Event_Schema ``pos_reconciliation_flagged``).
    """

    business_day: str
    mismatch_reason: str


class PaymentRefundedPayload(_PayloadModel):
    """``payment_refunded`` required properties (Data_Event_Schema L549-563)."""

    refund_type: str
    refund_reason: str


class SafetyReportCreatedPayload(_PayloadModel):
    """``safety_report_created`` required properties (Data_Event_Schema L569-586).

    Carries only classification + visibility + ids. The narrative is stored in a
    restricted table, never here (enforced by ``FORBIDDEN_SAFETY_PROPERTY_KEYS``).
    """

    safety_report_id: str
    reporter_type: str
    target_type: str
    report_type: str
    severity: str
    visibility: str


class SafetyReportResolvedPayload(_PayloadModel):
    """``safety_report_resolved`` — safety report closed."""

    safety_report_id: str
    resolution: str


class UserBlockedPayload(_PayloadModel):
    """``user_blocked`` required properties (Data_Event_Schema L592-607)."""

    block_id: str
    block_scope: str
    block_reason: str
    effective_from: str


class AdminNoteCreatedPayload(_PayloadModel):
    """``admin_note_created`` — operator note."""

    note_id: str


# Maps each registered event name to the schema validating its ``properties``.
# Emission looks the name up here; an unmapped name is rejected. This is the
# concrete enforcement of "every event has a known, validated shape".
EVENT_PAYLOAD_SCHEMAS: dict[str, type[_PayloadModel]] = {
    EventName.FAN_SIGNED_UP.value: FanSignedUpPayload,
    EventName.ANONYMOUS_USER_CREATED.value: AnonymousUserCreatedPayload,
    EventName.ANONYMOUS_USER_MERGED.value: AnonymousUserMergedPayload,
    EventName.RULE_CONSENT_GIVEN.value: RuleConsentGivenPayload,
    EventName.RESERVATION_CREATED.value: ReservationCreatedPayload,
    EventName.RESERVATION_CANCELLED.value: ReservationCancelledPayload,
    EventName.VISIT_CHECKED_IN.value: VisitCheckedInPayload,
    EventName.VISIT_COMPLETED.value: VisitCompletedPayload,
    EventName.VISIT_INVALIDATED.value: VisitInvalidatedPayload,
    EventName.CAST_PROFILE_VIEWED.value: CastProfileViewedPayload,
    EventName.SCHEDULE_VIEWED.value: ScheduleViewedPayload,
    EventName.FAVORITE_ADDED.value: FavoriteAddedPayload,
    EventName.FAVORITE_REMOVED.value: FavoriteRemovedPayload,
    EventName.CHEKI_RECORDED.value: ChekiRecordedPayload,
    EventName.EVENT_VIEWED.value: EventViewedPayload,
    EventName.EVENT_RESERVED.value: EventReservedPayload,
    EventName.COUPON_ISSUED.value: CouponIssuedPayload,
    EventName.COUPON_REDEEMED.value: CouponRedeemedPayload,
    EventName.POS_ORDER_LINKED.value: PosOrderLinkedPayload,
    EventName.POS_RECONCILIATION_FLAGGED.value: PosReconciliationFlaggedPayload,
    EventName.PAYMENT_REFUNDED.value: PaymentRefundedPayload,
    EventName.SAFETY_REPORT_CREATED.value: SafetyReportCreatedPayload,
    EventName.SAFETY_REPORT_RESOLVED.value: SafetyReportResolvedPayload,
    EventName.USER_BLOCKED.value: UserBlockedPayload,
    EventName.ADMIN_NOTE_CREATED.value: AdminNoteCreatedPayload,
}
