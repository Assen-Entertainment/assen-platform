"""Hosted-commerce bridge models — the integration seam for a hosted commerce SaaS.

If the platform adopts the "hosted commerce (Cafe24/아임웹) + custom fan platform"
hybrid, physical-goods transactions (cart/pay/ship) live on the SaaS while Assen keeps
the fan platform + the creator settlement ledger. This app mirrors the SaaS's orders as
:class:`ExternalCommerceOrder` (from inbound webhooks) and dedupes events via
:class:`WebhookReceipt`, so the settlement ledger (apps.payments) can attribute earnings
to a creator without Assen owning the transaction. Provider-agnostic; the whole surface
is fail-closed behind ``ENABLE_COMMERCE_BRIDGE``. Keeping it wired-but-off means BOTH the
full-custom and the hybrid tracks stay viable without re-architecting.

Carries NO card/PII — only an opaque external order id, a creator tag, an opaque buyer
ref (for the auth bridge), and amount/currency/status.
"""

from __future__ import annotations

import uuid

from django.db import models


class CommerceProvider(models.TextChoices):
    """The hosted commerce platform a webhook/order originated from."""

    CAFE24 = "cafe24", "cafe24"
    IMWEB = "imweb", "imweb"
    # A normalized/self-hosted sender (tests, or a headless integration that already
    # emits the canonical event shape). Real Cafe24/Imweb adapters translate into this.
    GENERIC = "generic", "generic"


class ExternalOrderStatus(models.TextChoices):
    """Lifecycle of a hosted-commerce order as reflected to Assen."""

    PAID = "paid", "paid"
    SHIPPED = "shipped", "shipped"
    CANCELLED = "cancelled", "cancelled"
    REFUNDED = "refunded", "refunded"


class ExternalCommerceOrder(models.Model):
    """A goods order that settled on a hosted commerce SaaS, mirrored for attribution.

    Assen does NOT own the transaction (PG/shipping live on the SaaS); this row exists
    only to attribute the sale to a creator and drive the settlement ledger
    (apps.payments, provider=external). Unique per (provider, external_order_id).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=16, choices=CommerceProvider.choices)
    external_order_id = models.CharField(max_length=128)
    # The creator the sold goods are attributed to. Assen keeps the catalog as the
    # source of truth and tags each product with a creator; the SaaS echoes that tag.
    # Nullable — an unattributed/house order stays null.
    creator = models.ForeignKey(
        "creator.Creator",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="external_orders",
    )
    # Opaque buyer reference the SaaS echoes back (e.g. the fan's ``fan_id`` that Assen
    # handed it at checkout) — resolved to an Assen account by the auth bridge. Never a
    # raw identity. Blank = guest/unlinked purchase.
    buyer_ref = models.CharField(max_length=128, blank=True, default="")
    amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="KRW")
    status = models.CharField(max_length=16, choices=ExternalOrderStatus.choices)
    received_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_order_id"], name="uniq_external_order"
            ),
        ]
        indexes = [
            models.Index(fields=["creator", "-received_at"]),
            models.Index(fields=["provider", "status"]),
        ]
        ordering = ["-received_at"]

    def __str__(self) -> str:
        """Identify the external order for admin/log display."""
        return f"ext-order:{self.provider}:{self.external_order_id}:{self.status}"


class WebhookReceipt(models.Model):
    """Idempotency ledger for inbound hosted-commerce webhooks (dedup by event id).

    A provider may retry a webhook; recording each ``external_event_id`` under a unique
    constraint makes ingestion idempotent — a duplicate delivery is a no-op.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=16, choices=CommerceProvider.choices)
    external_event_id = models.CharField(max_length=128)
    event_type = models.CharField(max_length=32)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_event_id"], name="uniq_webhook_event"
            ),
        ]
        ordering = ["-received_at"]

    def __str__(self) -> str:
        """Identify the webhook receipt for admin/log display."""
        return f"webhook:{self.provider}:{self.external_event_id}"
