"""Payment-attempt ledger helpers (ASS-298).

Small, side-effect-only writers that record a :class:`PaymentAttempt` for the
two settlement rails that exist today — the deterministic mock and an explicit
free grant (ASS-297). They must be called INSIDE the parent order/subscription's
``transaction.atomic()`` block so a rolled-back parent never leaves a dangling
attempt. No card data ever reaches here: only amounts, a currency, and an opaque
mock transaction id.
"""

from __future__ import annotations

from apps.commerce.models import Order
from apps.commerce_bridge.models import ExternalCommerceOrder
from apps.membership.models import Subscription
from apps.payments.models import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentProvider,
)


def record_mock_settlement(
    *,
    order: Order | None = None,
    subscription: Subscription | None = None,
    amount: int,
    idempotency_key: str | None = None,
) -> PaymentAttempt:
    """Record a succeeded MOCK settlement attempt for an order or subscription.

    Exactly one of ``order``/``subscription`` must be given (the model's XOR
    constraint enforces this). ``provider_txn_id`` is a deterministic mock id
    derived from the parent's id — never a real PG token, never a PAN.
    """
    target_id = order.id if order is not None else getattr(subscription, "id", "")
    return PaymentAttempt.objects.create(
        order=order,
        subscription=subscription,
        provider=PaymentProvider.MOCK,
        provider_txn_id=f"mock_{target_id}",
        authorized_amount=amount,
        currency="KRW",
        status=PaymentAttemptStatus.SUCCEEDED,
        idempotency_key=idempotency_key,
    )


def record_free_grant(
    *,
    order: Order | None = None,
    subscription: Subscription | None = None,
    idempotency_key: str | None = None,
) -> PaymentAttempt:
    """Record a succeeded FREE-grant attempt (ASS-297) for an order/subscription.

    A free grant settles nothing (``authorized_amount=0``, no ``provider_txn_id``)
    but is still ledgered so a free entitlement's provenance is auditable exactly
    like a paid one. Exactly one of ``order``/``subscription`` must be given.
    """
    return PaymentAttempt.objects.create(
        order=order,
        subscription=subscription,
        provider=PaymentProvider.FREE,
        authorized_amount=0,
        currency="KRW",
        status=PaymentAttemptStatus.SUCCEEDED,
        idempotency_key=idempotency_key,
    )


def record_external_settlement(
    *, external_order: ExternalCommerceOrder
) -> PaymentAttempt:
    """Record a succeeded EXTERNAL settlement for a hosted-commerce order (hybrid track).

    The sale settled on a hosted commerce SaaS (Cafe24/아임웹 — Assen does not own the
    transaction), so this is an attribution record crediting the creator: provider=
    ``external``, an opaque ``provider:external_order_id`` as the txn id, the order's
    amount/currency, status succeeded. Carries no card data. **Idempotent per external
    order** — a second call (webhook retries are expected) returns the existing succeeded
    attempt rather than double-crediting.
    """
    existing = PaymentAttempt.objects.filter(
        external_order=external_order,
        status=PaymentAttemptStatus.SUCCEEDED,
    ).first()
    if existing is not None:
        return existing
    return PaymentAttempt.objects.create(
        external_order=external_order,
        provider=PaymentProvider.EXTERNAL,
        provider_txn_id=f"{external_order.provider}:{external_order.external_order_id}",
        authorized_amount=external_order.amount,
        currency=external_order.currency,
        status=PaymentAttemptStatus.SUCCEEDED,
    )
