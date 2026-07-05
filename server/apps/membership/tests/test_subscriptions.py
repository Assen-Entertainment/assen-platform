"""Tests for the membership subscription flow (E11/B4 — mock, no money moves)."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
from django.db import IntegrityError
from django.test import Client

from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus

pytestmark = pytest.mark.django_db

BASE = "/api/subscriptions"
JSON = "application/json"


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    """Return a test-client headers mapping bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _tier(creator: Creator | None = None, **kwargs: object) -> MembershipTier:
    """Create a membership tier attached to a creator."""
    if creator is None:
        creator = Creator.objects.create(handle="stellar", name="별빛")
    defaults: dict[str, object] = {"name": "스탠다드", "price": 9900, "period": "월"}
    defaults.update(kwargs)
    return MembershipTier.objects.create(creator=creator, **defaults)


def test_subscribe_creates_active(client: Client) -> None:
    """Subscribing records an active subscription with creator/tier detail."""
    fan = _fan()
    tier = _tier()
    res = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "active"
    assert body["cancel_scheduled"] is False
    assert body["tier_name"] == "스탠다드"
    assert body["creator_handle"] == "stellar"
    assert body["price"] == 9900
    assert body["next_billing_date"]


def test_subscribe_unknown_tier_is_404(client: Client) -> None:
    """Subscribing to a non-existent tier is a 404."""
    fan = _fan()
    import uuid

    res = client.post(
        BASE,
        data=json.dumps({"tier_id": str(uuid.uuid4())}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 404


def test_duplicate_active_same_creator_is_422(client: Client) -> None:
    """A second active subscription to the same creator is refused (422)."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier_a = _tier(creator=creator, name="라이트", sort_order=0)
    tier_b = _tier(creator=creator, name="프리미엄", sort_order=1)
    first = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier_a.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert first.status_code == 201
    second = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier_b.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert second.status_code == 422


def test_duplicate_active_subscription_hits_db_constraint() -> None:
    """The (fan, creator) partial-unique constraint rejects a second active sub (B2).

    Simulates the concurrency the endpoint's exists()-check cannot fully close: a
    direct duplicate insert of a second ACTIVE subscription for the same
    (fan, creator) must raise ``IntegrityError`` — the DB backstop behind the
    endpoint's atomic-create → 422 path.
    """
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier_a = _tier(creator=creator, name="라이트", sort_order=0)
    tier_b = _tier(creator=creator, name="프리미엄", sort_order=1)

    Subscription.objects.create(
        fan=fan, tier=tier_a, status=SubscriptionStatus.ACTIVE, next_billing_date=date.today()
    )
    with pytest.raises(IntegrityError):
        Subscription.objects.create(
            fan=fan, tier=tier_b, status=SubscriptionStatus.ACTIVE, next_billing_date=date.today()
        )


def test_subscription_denormalises_creator_from_tier() -> None:
    """A subscription pins ``creator`` from its tier on save (B2)."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier = _tier(creator=creator)
    sub = Subscription.objects.create(
        fan=fan, tier=tier, status=SubscriptionStatus.ACTIVE, next_billing_date=date.today()
    )
    assert sub.creator_id == creator.id


def test_list_returns_only_own(client: Client) -> None:
    """The subscription list is scoped to the requesting fan."""
    fan = _fan()
    other = _fan()
    tier = _tier()
    client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert len(client.get(BASE, headers=_auth(fan)).json()) == 1
    assert client.get(BASE, headers=_auth(other)).json() == []


def test_cancel_marks_scheduled_and_is_idempotent_guard(client: Client) -> None:
    """Cancel schedules end-of-period (status stays active); a re-cancel is 422."""
    fan = _fan()
    tier = _tier()
    sub_id = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    ).json()["id"]
    res = client.post(f"{BASE}/{sub_id}/cancel", content_type=JSON, headers=_auth(fan))
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "active"
    assert body["cancel_scheduled"] is True
    # cancelled_at recorded but status kept active ("해지 예정").
    sub = Subscription.objects.get(id=sub_id)
    assert sub.status == SubscriptionStatus.ACTIVE.value
    assert sub.cancelled_at is not None

    again = client.post(f"{BASE}/{sub_id}/cancel", content_type=JSON, headers=_auth(fan))
    assert again.status_code == 422


def test_cancel_another_fans_subscription_is_404(client: Client) -> None:
    """Cancelling someone else's subscription is a 404 (no existence leak)."""
    owner = _fan()
    other = _fan()
    tier = _tier()
    sub_id = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(owner),
    ).json()["id"]
    res = client.post(f"{BASE}/{sub_id}/cancel", content_type=JSON, headers=_auth(other))
    assert res.status_code == 404


def test_subscribe_requires_auth(client: Client) -> None:
    """An anonymous caller cannot subscribe."""
    tier = _tier()
    res = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
    )
    assert res.status_code == 401


# --- tier change (up/downgrade, R5-W1A) --------------------------------------- #


def _subscribe(client: Client, fan: Account, tier: MembershipTier) -> str:
    """Subscribe ``fan`` to ``tier`` and return the subscription id."""
    sub_id: str = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    ).json()["id"]
    return sub_id


def _change(client: Client, fan: Account, sub_id: str, tier: MembershipTier) -> Any:
    """PATCH the subscription's tier."""
    return client.patch(
        f"{BASE}/{sub_id}",
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )


def test_change_tier_same_creator_succeeds(client: Client) -> None:
    """A fan can up/downgrade to another active tier of the same creator."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    light = _tier(creator=creator, name="라이트", price=5000, sort_order=0)
    premium = _tier(creator=creator, name="프리미엄", price=15000, sort_order=1)
    sub_id = _subscribe(client, fan, light)

    res = _change(client, fan, sub_id, premium)
    assert res.status_code == 200
    body = res.json()
    assert body["tier_name"] == "프리미엄"
    assert body["price"] == 15000
    assert Subscription.objects.get(id=sub_id).tier_id == premium.id


def test_change_tier_is_idempotent_noop(client: Client) -> None:
    """Switching to the tier already held is a 200 no-op."""
    fan = _fan()
    tier = _tier()
    sub_id = _subscribe(client, fan, tier)
    res = _change(client, fan, sub_id, tier)
    assert res.status_code == 200
    assert res.json()["tier_id"] == str(tier.id)


def test_change_tier_cross_creator_is_422(client: Client) -> None:
    """A tier belonging to another creator is not a valid target (422, no leak)."""
    fan = _fan()
    mine = Creator.objects.create(handle="stellar", name="별빛")
    other = Creator.objects.create(handle="rabbit", name="토끼")
    my_tier = _tier(creator=mine, name="라이트")
    foreign = _tier(creator=other, name="남의등급")
    sub_id = _subscribe(client, fan, my_tier)

    res = _change(client, fan, sub_id, foreign)
    assert res.status_code == 422
    assert res.json()["code"] == "TierNotFound"
    assert Subscription.objects.get(id=sub_id).tier_id == my_tier.id


def test_change_tier_to_inactive_is_422(client: Client) -> None:
    """An inactive (archived) target tier cannot be switched to."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    active = _tier(creator=creator, name="라이트")
    archived = _tier(creator=creator, name="보관", active=False)
    sub_id = _subscribe(client, fan, active)

    res = _change(client, fan, sub_id, archived)
    assert res.status_code == 422
    assert res.json()["code"] == "TierNotFound"


def test_change_tier_on_non_active_subscription_is_422(client: Client) -> None:
    """A cancelled subscription cannot change tiers."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier_a = _tier(creator=creator, name="라이트", sort_order=0)
    tier_b = _tier(creator=creator, name="프리미엄", sort_order=1)
    sub = Subscription.objects.create(
        fan=fan,
        tier=tier_a,
        status=SubscriptionStatus.CANCELLED,
        next_billing_date=date.today(),
    )
    res = _change(client, fan, str(sub.id), tier_b)
    assert res.status_code == 422
    assert res.json()["code"] == "SubscriptionNotActive"


def test_change_tier_another_fans_subscription_is_404(client: Client) -> None:
    """Changing someone else's subscription is a 404 (no existence leak)."""
    owner = _fan()
    other = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier_a = _tier(creator=creator, name="라이트", sort_order=0)
    tier_b = _tier(creator=creator, name="프리미엄", sort_order=1)
    sub_id = _subscribe(client, owner, tier_a)
    res = _change(client, other, sub_id, tier_b)
    assert res.status_code == 404
