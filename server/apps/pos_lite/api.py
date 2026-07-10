"""Operator API for manual POS order linking (ASS-102 v0).

Surfaces the POS-vendor-independent slice (P0_Scope_Reconciliation G-2): link a
POS receipt/order to a visit, list the day's links, void a wrong link, and read
the daily link coverage (the "POS 연결률" KPI input / 미연결 목록). CSV import +
daily sales reconciliation are held (OQ-C) and are not exposed here.
"""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from pydantic import Field

from apps.admin_rbac.permissions import operator_required
from apps.identity.auth import authed
from apps.identity.models import Account
from apps.pos_lite.models import PosOrder, PosOrderStatus
from apps.pos_lite.services import link_pos_order, void_pos_order
from apps.visit.models import VisitRecord, VisitRecordStatus
from config.api import api

router = Router(auth=operator_required, tags=["operator-pos"])

_FREE_TEXT_MAX = 500


class PosError(Schema):
    """Stable error shape for operator POS endpoints."""

    detail: str


class PosOrderOut(Schema):
    """POS link fields exposed to operator tools (no fan personal data)."""

    id: uuid.UUID
    visit_id: uuid.UUID
    pos_receipt_no: str
    pos_order_id: str
    business_day: date_type
    payment_status: str
    payment_method: str
    amount: Decimal | None
    link_method: str
    linked_confidence: str
    pos_vendor_name: str
    reconciliation_status: str
    status: str
    void_reason: str
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class PosOrderCreateIn(Schema):
    """Payload for an operator manual POS link.

    At least one of ``pos_receipt_no``/``pos_order_id`` is required (enforced in
    the service). ``amount`` is the POS-reported total; omit it when unconfirmed.
    """

    visit_id: uuid.UUID
    pos_receipt_no: str = Field(default="", max_length=64)
    pos_order_id: str = Field(default="", max_length=64)
    business_day: date_type | None = None
    payment_status: str = "unknown"
    payment_method: str = "unknown"
    amount: Decimal | None = Field(default=None, ge=0)
    pos_vendor_name: str = Field(default="", max_length=64)
    linked_confidence: str = "manual"
    refund_reason: str = Field(default="", max_length=_FREE_TEXT_MAX)


class PosOrderVoidIn(Schema):
    """Reason required when voiding a POS link."""

    reason: str = Field(max_length=_FREE_TEXT_MAX)


class UnlinkedVisitOut(Schema):
    """A visit with no active POS link (a 미연결 항목)."""

    visit_id: uuid.UUID
    visited_at: datetime
    store_id: str


class PosLinkCoverageOut(Schema):
    """Daily POS link coverage — the POS 연결률 KPI surface.

    ``link_rate`` is ``linked_visits / total_active_visits`` (0.0 when there are
    no visits), a ratio not a money figure.
    """

    business_day: date_type
    total_active_visits: int
    linked_visits: int
    unlinked_visits: int
    link_rate: float
    unlinked: list[UnlinkedVisitOut]


@router.post("/orders", response={201: PosOrderOut, 400: PosError, 404: PosError})
def create_pos_order(
    request: HttpRequest,
    payload: PosOrderCreateIn,
) -> tuple[int, PosOrderOut | PosError]:
    """Manually link a POS order/receipt to a visit."""
    visit = get_object_or_404(VisitRecord, id=payload.visit_id)
    try:
        record = link_pos_order(
            visit=visit,
            actor=_actor(request),
            pos_receipt_no=payload.pos_receipt_no,
            pos_order_id=payload.pos_order_id,
            payment_status=payload.payment_status,
            payment_method=payload.payment_method,
            amount=payload.amount,
            pos_vendor_name=payload.pos_vendor_name,
            linked_confidence=payload.linked_confidence,
            refund_reason=payload.refund_reason,
            business_day=payload.business_day,
        )
    except ValueError as exc:
        return 400, PosError(detail=str(exc))
    return 201, _order_out(record)


@router.get("/orders", response=list[PosOrderOut])
def list_pos_orders(
    request: HttpRequest,
    date: date_type | None = None,
) -> list[PosOrderOut]:
    """List POS links for a business day (default today), including voided rows."""
    del request
    day = date or timezone.localdate()
    records = PosOrder.objects.filter(business_day=day).order_by("-created_at")
    return [_order_out(record) for record in records]


@router.post("/orders/{order_id}/void", response={200: PosOrderOut, 400: PosError, 404: PosError})
def void_pos_order_endpoint(
    request: HttpRequest,
    order_id: uuid.UUID,
    payload: PosOrderVoidIn,
) -> tuple[int, PosOrderOut | PosError]:
    """Void a POS link with a mandatory operator reason."""
    order = get_object_or_404(PosOrder, id=order_id)
    try:
        voided = void_pos_order(order=order, reason=payload.reason, actor=_actor(request))
    except ValueError as exc:
        return 400, PosError(detail=str(exc))
    return 200, _order_out(voided)


@router.get("/coverage", response=PosLinkCoverageOut)
def pos_link_coverage(
    request: HttpRequest,
    date: date_type | None = None,
) -> PosLinkCoverageOut:
    """Report the day's POS link coverage + the unlinked-visit list (연결률)."""
    del request
    day = date or timezone.localdate()
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = start + timedelta(days=1)
    visits = list(
        VisitRecord.objects.filter(
            visited_at__gte=start,
            visited_at__lt=end,
            status=VisitRecordStatus.ACTIVE.value,
        ).order_by("-visited_at", "-created_at")
    )
    linked_ids = set(
        PosOrder.objects.filter(
            visit__in=visits,
            status=PosOrderStatus.ACTIVE.value,
        ).values_list("visit_id", flat=True)
    )
    unlinked = [
        UnlinkedVisitOut(visit_id=v.id, visited_at=v.visited_at, store_id=v.store_id)
        for v in visits
        if v.id not in linked_ids
    ]
    total = len(visits)
    linked = total - len(unlinked)
    return PosLinkCoverageOut(
        business_day=day,
        total_active_visits=total,
        linked_visits=linked,
        unlinked_visits=len(unlinked),
        link_rate=(linked / total) if total else 0.0,
        unlinked=unlinked,
    )


def _actor(request: HttpRequest) -> Account:
    """Return the authenticated operator account supplied by RoleRequired."""
    # request.auth is untyped without Ninja stubs (same idiom as visit/api.py).
    return authed(request)


def _order_out(record: PosOrder) -> PosOrderOut:
    """Build the response schema for a POS link."""
    return PosOrderOut(
        id=record.id,
        visit_id=record.visit_id,
        pos_receipt_no=record.pos_receipt_no,
        pos_order_id=record.pos_order_id,
        business_day=record.business_day,
        payment_status=record.payment_status,
        payment_method=record.payment_method,
        amount=record.amount,
        link_method=record.link_method,
        linked_confidence=record.linked_confidence,
        pos_vendor_name=record.pos_vendor_name,
        reconciliation_status=record.reconciliation_status,
        status=record.status,
        void_reason=record.void_reason,
        created_by_id=record.created_by_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


api.add_router("/operator/pos", router)
