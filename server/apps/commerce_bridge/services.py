"""Hosted-commerce bridge services: ingest webhooks, attribute, settle, resolve buyers.

The ingest path is the heart of the hybrid seam: verify → dedup → mirror the external
order → (on the paid event) credit the creator in the shared settlement ledger. Every
external dependency is looked up lazily so this module stays import-cycle free.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import IntegrityError, transaction

if TYPE_CHECKING:
    from apps.creator.models import Creator
    from apps.identity.models import Account

from apps.commerce_bridge.adapters import NormalizedEvent, adapter_for
from apps.commerce_bridge.models import (
    CommerceProvider,
    ExternalCommerceOrder,
    ExternalOrderStatus,
    WebhookReceipt,
)


class CommerceBridgeDisabled(Exception):
    """Raised when the bridge is off / unconfigured (fail-closed)."""


_EVENT_STATUS: dict[str, str] = {
    "order_paid": ExternalOrderStatus.PAID.value,
    "order_shipped": ExternalOrderStatus.SHIPPED.value,
    "order_cancelled": ExternalOrderStatus.CANCELLED.value,
    "order_refunded": ExternalOrderStatus.REFUNDED.value,
}


def ingest_webhook(
    *, provider: str, headers: Mapping[str, str], raw_body: bytes
) -> ExternalCommerceOrder | None:
    """Verify → dedup → record an inbound hosted-commerce webhook. Fail-closed.

    Returns the created/updated :class:`ExternalCommerceOrder`, or ``None`` when the
    event was a duplicate already processed. Raises :class:`CommerceBridgeDisabled` when
    the bridge is off/unconfigured, ``WebhookVerificationError`` on a bad signature/body,
    and ``ValueError`` on an unknown provider/event type.
    """
    if not settings.ENABLE_COMMERCE_BRIDGE:
        raise CommerceBridgeDisabled("commerce bridge is disabled")
    if provider not in CommerceProvider.values:
        raise ValueError(f"unknown provider '{provider}'")
    adapter = adapter_for(provider)
    if adapter is None:
        raise ValueError(f"no adapter for provider '{provider}'")

    adapter.verify(
        secret=settings.COMMERCE_BRIDGE_WEBHOOK_SECRET,
        headers=headers,
        raw_body=raw_body,
    )
    event = adapter.parse(raw_body=raw_body)
    status = _EVENT_STATUS.get(event.event_type)
    if status is None:
        raise ValueError(f"unknown event type '{event.event_type}'")

    with transaction.atomic():
        # Idempotency: a duplicate event id is a no-op (unique constraint on
        # provider+external_event_id). Recorded before applying so a retry never
        # double-settles.
        try:
            WebhookReceipt.objects.create(
                provider=provider,
                external_event_id=event.event_id,
                event_type=event.event_type,
            )
        except IntegrityError:
            return None
        return _apply_event(provider=provider, event=event, status=status)


def _apply_event(
    *, provider: str, event: NormalizedEvent, status: str
) -> ExternalCommerceOrder:
    """Upsert the external order and, on the paid event, record the settlement."""
    order, _created = ExternalCommerceOrder.objects.update_or_create(
        provider=provider,
        external_order_id=event.external_order_id,
        defaults={
            "creator": _resolve_creator(event.creator_ref),
            "buyer_ref": event.buyer_ref,
            "amount": event.amount,
            "currency": event.currency,
            "status": status,
        },
    )
    if status == ExternalOrderStatus.PAID.value:
        # Lazy import — payments references us by string FK; import here to avoid a cycle.
        from apps.payments.services import record_external_settlement

        record_external_settlement(external_order=order)
    return order


def _resolve_creator(creator_ref: str) -> Creator | None:
    """Map the provider's creator tag (a handle) to a Creator, or None."""
    from apps.creator.models import Creator

    if not creator_ref:
        return None
    return Creator.objects.filter(handle=creator_ref).first()


def resolve_buyer(buyer_ref: str) -> Account | None:
    """Auth bridge: map a hosted-commerce ``buyer_ref`` to an Assen account, or None.

    The SaaS echoes back the opaque ``buyer_ref`` Assen handed it at checkout (the fan's
    ``fan_id``), so a goods purchase can be tied to the platform account without sharing
    a raw identity across systems. A blank/invalid ref or a withdrawn account → None
    (guest/unlinked). Never raises on a malformed ref.
    """
    from apps.identity.models import Account

    if not buyer_ref:
        return None
    try:
        uuid.UUID(str(buyer_ref))
    except (ValueError, AttributeError, TypeError):
        return None
    return Account.objects.filter(fan_id=buyer_ref, is_active=True).first()
