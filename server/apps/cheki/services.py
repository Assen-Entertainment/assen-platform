"""Service layer for operator-managed cheki records.

Every cheki mutation passes through this module so the operational row, the audit
trail, and the append-only analytics event stay coupled. Analytics events are
emitted **only** through :func:`apps.event_log.services.emit_event` (validated
registry) — mirrors the visit domain (ASS-94).

Event mapping (Data_Event_Schema):

- record  → ``cheki_recorded``     (cast-count + POS-reconciliation source)
- void    → ``cheki_invalidated``  (the canonical exclusion event)
- correct → **audit only**; editing metadata is operational, not an analytics
  fact, so it has no canonical event.

The settled value is never written here — settlement stays a status
(candidate/hold/excluded), a human-gated decision (Data 제약).
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.cheki.models import (
    ChekiRecord,
    ChekiRecordStatus,
    ChekiSettlementStatus,
    ChekiType,
)
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import emit_event
from apps.identity.models import Account
from apps.visit.models import VisitRecord, VisitRecordStatus


@transaction.atomic
def record_cheki(
    *,
    visit: VisitRecord,
    cast_id: str,
    cheki_type: str,
    quantity: int,
    actor: Account,
    image_stored: bool = False,
    consent_scope: str = "",
    pos_receipt_no: str = "",
) -> ChekiRecord:
    """Create a cheki record and emit its audit + analytics side effects.

    The fan (if any) is taken from the visit so an anonymous-visit cheki simply
    has no fan. A ``cheki_type=test`` record is born settlement-excluded since it
    must never count toward sales or MSFC.

    A cheki cannot be recorded against a voided visit: the visit never happened,
    so a settlement *candidate* hanging off it would leak into reconciliation.
    """
    if visit.status == VisitRecordStatus.VOIDED.value:
        raise ValueError("Cannot record a cheki against a voided visit.")
    # A test cheki is born settlement-excluded so it never counts toward sales.
    settlement = (
        ChekiSettlementStatus.EXCLUDED.value
        if cheki_type == ChekiType.TEST.value
        else ChekiSettlementStatus.CANDIDATE.value
    )
    record = ChekiRecord.objects.create(
        fan=visit.fan,
        visit=visit,
        cast_id=cast_id,
        cheki_type=cheki_type,
        quantity=quantity,
        image_stored=image_stored,
        consent_scope=consent_scope,
        pos_receipt_no=pos_receipt_no,
        settlement_status=settlement,
        created_by=actor,
    )
    record_audit(
        actor=actor,
        action=AuditAction.CHEKI_RECORDED.value,
        target=str(record.id),
        metadata={
            "cast_id": cast_id,
            "cheki_type": cheki_type,
            "quantity": quantity,
        },
    )
    # fan is currently always set (VisitRecord.fan is non-null); the empty-fan
    # branch is forward-compat for anonymous check-ins (cheki_recorded fan_id is
    # 조건부, Data_Event_Schema L465) and is not yet reachable.
    fan_id = str(record.fan.fan_id) if record.fan is not None else ""
    payload = {
        "visit_id": str(visit.id),
        "cast_id": cast_id,
        "cheki_id": str(record.id),
        "cheki_type": cheki_type,
        "quantity": quantity,
        "image_stored": image_stored,
    }
    if consent_scope:
        # The consent basis travels with the event when an image was stored.
        payload["consent_scope"] = consent_scope
    emit_event(
        event_name=EventName.CHEKI_RECORDED.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_id=str(actor.fan_id),
        fan_id=fan_id,
        cast_id=cast_id,
        visit_id=str(visit.id),
        # An operator records a genuine cheki sale; it is not excluded traffic.
        actor_is_operator=False,
        ids={
            "fan_id": fan_id,
            "visit_id": str(visit.id),
            "cast_id": cast_id,
            "cheki_id": str(record.id),
        },
        context={"store_id": record.store_id},
        payload=payload,
        quality={"created_by_operator_id": str(actor.fan_id)},
    )
    return record


@transaction.atomic
def correct_cheki(
    record: ChekiRecord,
    *,
    cheki_type: str | None = None,
    quantity: int | None = None,
    consent_scope: str | None = None,
    pos_receipt_no: str | None = None,
    actor: Account,
) -> ChekiRecord:
    """Correct mutable cheki fields, recording before/after audit evidence.

    No analytics event is emitted (operational correction; the canonical schema
    has no ``cheki_corrected`` event) — the audit log carries the trail.
    """
    if (
        cheki_type is None
        and quantity is None
        and consent_scope is None
        and pos_receipt_no is None
    ):
        return record
    before = _snapshot(record)
    update_fields = ["updated_at"]
    if cheki_type is not None:
        record.cheki_type = cheki_type
        update_fields.append("cheki_type")
    if quantity is not None:
        record.quantity = quantity
        update_fields.append("quantity")
    if consent_scope is not None:
        record.consent_scope = consent_scope
        update_fields.append("consent_scope")
    if pos_receipt_no is not None:
        record.pos_receipt_no = pos_receipt_no
        update_fields.append("pos_receipt_no")

    record.save(update_fields=update_fields)
    record.refresh_from_db()
    record_audit(
        actor=actor,
        action=AuditAction.CHEKI_CORRECTED.value,
        target=str(record.id),
        metadata={"before": before, "after": _snapshot(record)},
    )
    return record


@transaction.atomic
def void_cheki(*, record: ChekiRecord, reason: str, actor: Account) -> ChekiRecord:
    """Void a cheki record (never delete) and emit the exclusion event.

    The row flips to ``voided`` and ``settlement_status=excluded`` (a void can
    never settle), and the canonical ``cheki_invalidated`` event is appended so
    analytics excludes it. Re-voiding is rejected.
    """
    if record.status == ChekiRecordStatus.VOIDED.value:
        raise ValueError("Cheki record is already voided.")
    if not reason.strip():
        raise ValueError("Void reason is required.")

    before = _snapshot(record)
    record.status = ChekiRecordStatus.VOIDED.value
    record.void_reason = reason.strip()
    record.settlement_status = ChekiSettlementStatus.EXCLUDED.value
    record.save(update_fields=["status", "void_reason", "settlement_status", "updated_at"])
    record.refresh_from_db()
    record_audit(
        actor=actor,
        action=AuditAction.CHEKI_VOIDED.value,
        target=str(record.id),
        reason=record.void_reason,
        metadata={"before": before, "after": _snapshot(record)},
    )
    fan_id = str(record.fan.fan_id) if record.fan is not None else ""
    emit_event(
        event_name=EventName.CHEKI_INVALIDATED.value,
        occurred_at=timezone.now(),
        actor_type=ActorType.OPERATOR.value,
        source=EventSource.MANUAL.value,
        actor_id=str(actor.fan_id),
        fan_id=fan_id,
        cast_id=record.cast_id,
        visit_id=str(record.visit_id),
        actor_is_operator=False,
        ids={"cheki_id": str(record.id), "visit_id": str(record.visit_id)},
        context={"store_id": record.store_id},
        payload={"cheki_id": str(record.id), "reason": record.void_reason},
    )
    return record


def _snapshot(record: ChekiRecord) -> dict[str, object]:
    """Return the fields reviewers need to compare a cheki mutation."""
    return {
        "cheki_type": record.cheki_type,
        "quantity": record.quantity,
        "consent_scope": record.consent_scope,
        "pos_receipt_no": record.pos_receipt_no,
        "settlement_status": record.settlement_status,
        "status": record.status,
        "void_reason": record.void_reason,
    }
