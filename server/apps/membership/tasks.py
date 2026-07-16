"""Mock subscription billing worker (Codex #5).

The membership subscribe/tier-change endpoints record a mock settlement at write
time but never advance a subscription's period afterwards, so a cancelled sub stays
``active`` (entitled) forever past its billing date and a renewing sub is never
re-billed. :func:`run_subscription_billing_cycle` is the periodic job that closes
that gap: it EXPIRES cancelled/non-renewing subs whose period has ended and RENEWS
active non-cancelled ones (mock settlement + advanced period). Registered in
``CELERY_BEAT_SCHEDULE`` (config.settings.base).

MOCK only — no real gateway is called. Renewal writes a deterministic mock
settlement (the same rail as subscribe) at the subscription's AGREED price (#16),
never the tier's current price. The task is idempotent per period: each due row is
row-locked and re-checked inside the lock, and advancing ``current_period_end`` past
``now`` removes the row from the next run's candidate set, so running twice in one
period never double-bills.
"""

from __future__ import annotations

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.membership.models import BILLING_CYCLE, Subscription, SubscriptionStatus
from apps.payments.services import record_mock_settlement


@shared_task  # type: ignore[untyped-decorator]  # celery's decorator is untyped
def run_subscription_billing_cycle() -> dict[str, int]:
    """Expire ended cancelled subs and renew active ones; return per-outcome counts.

    Only paid subscriptions participate (``current_period_end`` is set); free/legacy
    memberships have no billing period and are skipped. Returns
    ``{"expired": n, "renewed": m}``.
    """
    now = timezone.now()
    # Candidate set: active, paid (period set), and past their period end. Snapshot the
    # ids up front so the per-row locking below isn't held across the whole scan.
    due_ids = list(
        Subscription.objects.filter(
            status=SubscriptionStatus.ACTIVE.value,
            current_period_end__isnull=False,
            current_period_end__lte=now,
        ).values_list("id", flat=True)
    )
    expired = 0
    renewed = 0
    for sub_id in due_ids:
        with transaction.atomic():
            sub = (
                Subscription.objects.select_for_update()
                .filter(id=sub_id)
                .first()
            )
            if sub is None:
                continue
            period_end = sub.current_period_end
            # Re-check under the row lock (idempotency + concurrency): a parallel run
            # may have already renewed (period_end now in the future) or expired it.
            if (
                sub.status != SubscriptionStatus.ACTIVE.value
                or period_end is None
                or period_end > now
            ):
                continue
            if sub.cancelled_at is not None:
                # Scheduled to not renew — the period has ended, so expire it.
                sub.status = SubscriptionStatus.EXPIRED.value
                sub.save(update_fields=["status"])
                expired += 1
                continue
            # Renew: advance the period and ledger a fresh mock settlement at the
            # AGREED price (#16), never the tier's current (mutable) price.
            sub.current_period_end = period_end + BILLING_CYCLE
            sub.next_billing_date = sub.current_period_end.date()
            sub.save(update_fields=["current_period_end", "next_billing_date"])
            amount = (
                sub.agreed_price if sub.agreed_price is not None else sub.tier.price
            )
            record_mock_settlement(subscription=sub, amount=amount)
            renewed += 1
    return {"expired": expired, "renewed": renewed}
