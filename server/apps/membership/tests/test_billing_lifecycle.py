"""Subscription billing lifecycle — agreed-terms snapshot + state machine (Codex #5, #16).

Covers the two audit findings end to end:

- **#16 immutable agreed terms:** a subscription is billed and displayed on the terms
  it agreed to (``agreed_price``/``agreed_period``/``agreed_tier_name``), so a creator
  later editing the tier never re-terms an existing member — including on renewal.
- **#16 financial history is PROTECTed:** a tier with settlement history soft-archives
  instead of erasing its subscriptions/payment attempts.
- **#5 billing state machine:** cancellation keeps entitlement until period end, then the
  worker expires it; the worker renews active subs (mock settlement + advanced period)
  and is idempotent per period; an expired sub is not an active subscription.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import (
    BILLING_CYCLE,
    MembershipTier,
    Subscription,
    SubscriptionStatus,
)
from apps.membership.services import active_subscription
from apps.membership.tasks import run_subscription_billing_cycle
from apps.payments.models import PaymentAttempt, PaymentAttemptStatus, PaymentProvider

pytestmark = pytest.mark.django_db

BASE = "/api/subscriptions"
STUDIO = "/api/studio/tiers"
JSON = "application/json"


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    """Return test-client headers bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _creator(handle: str = "stellar", owner: Account | None = None) -> Creator:
    """Create a creator, optionally owned by ``owner`` (for studio writes)."""
    return Creator.objects.create(handle=handle, name="별빛", owner=owner)


def _tier(creator: Creator, **kwargs: object) -> MembershipTier:
    """Create a membership tier attached to ``creator``."""
    defaults: dict[str, object] = {"name": "라이트", "price": 5000, "period": "월"}
    defaults.update(kwargs)
    return MembershipTier.objects.create(creator=creator, **defaults)


def _subscribe(client: Client, fan: Account, tier: MembershipTier) -> Subscription:
    """Subscribe ``fan`` to ``tier`` via the real API (captures agreed terms + ledger)."""
    res = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201, res.content
    return Subscription.objects.get(fan=fan, tier=tier)


def _rewind_period(sub: Subscription, *, days_ago: int = 1) -> None:
    """Move ``sub``'s period end into the past so the worker treats it as due."""
    past = timezone.now() - timedelta(days=days_ago)
    Subscription.objects.filter(id=sub.id).update(
        current_period_end=past, next_billing_date=past.date()
    )


# --------------------------------------------------------------------------- #
# #16 — immutable agreed terms
# --------------------------------------------------------------------------- #
def test_agreed_terms_survive_a_later_tier_price_change(client: Client) -> None:
    """An existing member keeps their agreed price/period after the creator edits the tier."""
    fan = _fan()
    creator = _creator()
    tier = _tier(creator, name="라이트", price=5000, period="월")
    _subscribe(client, fan, tier)

    # Creator re-terms the tier: ₩5,000/월 → ₩50,000/년, and renames it.
    tier.price = 50000
    tier.period = "년"
    tier.name = "프리미엄"
    tier.save(update_fields=["price", "period", "name"])

    listed = client.get(BASE, headers=_auth(fan)).json()
    assert len(listed) == 1
    row = listed[0]
    # The member's view reflects the AGREED terms, not the tier's live ones.
    assert row["price"] == 5000
    assert row["period"] == "월"
    assert row["tier_name"] == "라이트"


def test_renewal_bills_agreed_price_not_current_tier_price(client: Client) -> None:
    """A mock renewal settles the agreed price even after the creator raised the tier."""
    fan = _fan()
    creator = _creator()
    tier = _tier(creator, price=5000)
    sub = _subscribe(client, fan, tier)

    # Creator hikes the price; the in-flight member must not be re-billed at the new rate.
    tier.price = 50000
    tier.save(update_fields=["price"])

    _rewind_period(sub)
    result = run_subscription_billing_cycle()
    assert result == {"expired": 0, "renewed": 1}

    # Two attempts: the initial subscribe + one renewal, both at the agreed ₩5,000.
    amounts = list(
        PaymentAttempt.objects.filter(subscription=sub)
        .order_by("created_at")
        .values_list("authorized_amount", flat=True)
    )
    assert amounts == [5000, 5000]


# --------------------------------------------------------------------------- #
# #16 — financial history is PROTECTed (tier soft-archives, never erased)
# --------------------------------------------------------------------------- #
def test_tier_with_settlement_history_soft_archives_instead_of_erasing(
    client: Client,
) -> None:
    """Deleting a tier that has settlement history archives it; the ledger survives."""
    owner = _fan()
    creator = _creator(owner=owner)
    fan = _fan()
    tier = _tier(creator, price=5000)
    sub = _subscribe(client, fan, tier)
    # Take the subscription out of ACTIVE (period ended) but keep its settlement history.
    Subscription.objects.filter(id=sub.id).update(
        status=SubscriptionStatus.EXPIRED.value
    )

    res = client.delete(f"{STUDIO}/{tier.id}", headers=_auth(owner))
    assert res.status_code == 200
    assert res.json()["status"] == "archived"

    # The tier is soft-archived (hidden), not destroyed; sub + ledger are preserved.
    tier.refresh_from_db()
    assert tier.active is False
    assert Subscription.objects.filter(id=sub.id).exists()
    assert PaymentAttempt.objects.filter(subscription=sub).count() == 1


# --------------------------------------------------------------------------- #
# #5 — billing state machine: cancel → entitled until period end → worker expires
# --------------------------------------------------------------------------- #
def test_cancel_keeps_entitlement_until_period_end_then_worker_expires(
    client: Client,
) -> None:
    """Cancellation stays entitled until period end; the worker then expires it."""
    fan = _fan()
    creator = _creator()
    tier = _tier(creator, price=5000)
    sub = _subscribe(client, fan, tier)

    cancelled = client.post(
        f"{BASE}/{sub.id}/cancel", content_type=JSON, headers=_auth(fan)
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["cancel_scheduled"] is True

    # Still entitled: status active, period end in the future.
    sub.refresh_from_db()
    assert sub.status == SubscriptionStatus.ACTIVE.value
    assert active_subscription(fan, creator) is not None

    # The period ends → the worker expires the non-renewing sub (no renewal settlement).
    _rewind_period(sub)
    result = run_subscription_billing_cycle()
    assert result == {"expired": 1, "renewed": 0}

    sub.refresh_from_db()
    assert sub.status == SubscriptionStatus.EXPIRED.value
    assert active_subscription(fan, creator) is None
    # Only the original subscribe settlement — expiry never bills.
    assert PaymentAttempt.objects.filter(subscription=sub).count() == 1


def test_cancelled_sub_loses_entitlement_at_period_end_before_worker_runs(
    client: Client,
) -> None:
    """Entitlement closes at period end even if the worker has not yet flipped status."""
    fan = _fan()
    creator = _creator()
    tier = _tier(creator, price=5000)
    sub = _subscribe(client, fan, tier)
    client.post(f"{BASE}/{sub.id}/cancel", content_type=JSON, headers=_auth(fan))

    # Period end passes but the worker has not run: status is still ACTIVE.
    _rewind_period(sub)
    sub.refresh_from_db()
    assert sub.status == SubscriptionStatus.ACTIVE.value
    # Entitlement is nonetheless closed (cancelled + past current_period_end).
    assert active_subscription(fan, creator) is None


# --------------------------------------------------------------------------- #
# #5 — renewal worker: advances the period, ledgers a settlement, idempotent
# --------------------------------------------------------------------------- #
def test_renewal_worker_advances_period_and_ledgers_settlement(
    client: Client,
) -> None:
    """Renewing an active sub advances its period and writes one mock settlement."""
    fan = _fan()
    creator = _creator()
    tier = _tier(creator, price=5000)
    sub = _subscribe(client, fan, tier)
    _rewind_period(sub)
    before_end = Subscription.objects.get(id=sub.id).current_period_end
    assert before_end is not None

    result = run_subscription_billing_cycle()
    assert result == {"expired": 0, "renewed": 1}

    sub.refresh_from_db()
    assert sub.status == SubscriptionStatus.ACTIVE.value
    assert sub.current_period_end is not None
    assert sub.current_period_end == before_end + BILLING_CYCLE
    assert sub.current_period_end > timezone.now()

    renewal = PaymentAttempt.objects.filter(subscription=sub).order_by("created_at")[1]
    assert renewal.provider == PaymentProvider.MOCK
    assert renewal.status == PaymentAttemptStatus.SUCCEEDED
    assert renewal.authorized_amount == 5000


def test_renewal_worker_is_idempotent_within_a_period(client: Client) -> None:
    """Running the worker twice in one period never double-bills."""
    fan = _fan()
    creator = _creator()
    tier = _tier(creator, price=5000)
    sub = _subscribe(client, fan, tier)
    _rewind_period(sub)

    first = run_subscription_billing_cycle()
    second = run_subscription_billing_cycle()
    assert first == {"expired": 0, "renewed": 1}
    assert second == {"expired": 0, "renewed": 0}

    # Exactly one renewal was added on top of the initial subscribe settlement.
    assert PaymentAttempt.objects.filter(subscription=sub).count() == 2


def test_free_subscription_is_not_touched_by_the_worker() -> None:
    """A free membership (no billing period) is never renewed or expired."""
    fan = _fan()
    creator = _creator()
    tier = _tier(creator, price=0)
    sub = Subscription.objects.create(
        fan=fan,
        tier=tier,
        status=SubscriptionStatus.ACTIVE.value,
        agreed_price=0,
        agreed_period="월",
        agreed_tier_name="라이트",
        current_period_end=None,
        next_billing_date=None,
    )

    result = run_subscription_billing_cycle()
    assert result == {"expired": 0, "renewed": 0}
    sub.refresh_from_db()
    assert sub.status == SubscriptionStatus.ACTIVE.value


# --------------------------------------------------------------------------- #
# #5 — an expired subscription is not an active subscription
# --------------------------------------------------------------------------- #
def test_expired_subscription_is_not_active_subscription() -> None:
    """An ``expired`` subscription grants no entitlement."""
    fan = _fan()
    creator = _creator()
    tier = _tier(creator, price=5000)
    Subscription.objects.create(
        fan=fan,
        tier=tier,
        status=SubscriptionStatus.EXPIRED.value,
        agreed_price=5000,
        agreed_period="월",
        agreed_tier_name="라이트",
        current_period_end=timezone.now() - timedelta(days=1),
    )
    assert active_subscription(fan, creator) is None
