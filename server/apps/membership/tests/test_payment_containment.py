"""ASS-286 — payment containment (membership).

With ``ENABLE_MOCK_PAYMENT`` off, a new subscription and a tier change must fail
closed with a coded 503 and change nothing — no ACTIVE subscription minted, no
tier swapped. Gating on the flag (not on a tokenizer, which only tokenizes a
card and is not authorization/capture).
"""

from __future__ import annotations

import json

import pytest
from django.test import Client, override_settings

from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier, Subscription
from config.errors import ErrorCode

pytestmark = pytest.mark.django_db

BASE = "/api/subscriptions"
JSON = "application/json"


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    """Return a test-client headers mapping bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _tier(creator: Creator, **kwargs: object) -> MembershipTier:
    """Create a membership tier attached to ``creator``."""
    defaults: dict[str, object] = {"name": "스탠다드", "price": 9900, "period": "월"}
    defaults.update(kwargs)
    return MembershipTier.objects.create(creator=creator, **defaults)


@override_settings(ENABLE_MOCK_PAYMENT=False)
def test_subscribe_fails_closed(client: Client) -> None:
    """mock off → 503 PaymentsUnavailable, no subscription created."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier = _tier(creator)
    res = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 503
    assert res.json()["code"] == str(ErrorCode.PAYMENTS_UNAVAILABLE)
    assert Subscription.objects.count() == 0


def test_change_tier_fails_closed_and_keeps_tier(client: Client) -> None:
    """mock off → an existing active sub cannot switch tiers (503, tier unchanged).

    The sub is created through the API with the mock on (so every field is set),
    then the tier change is attempted with the mock off.
    """
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier1 = _tier(creator, name="스탠다드", price=9900)
    tier2 = _tier(creator, name="프리미엄", price=19900)
    with override_settings(ENABLE_MOCK_PAYMENT=True):
        created = client.post(
            BASE,
            data=json.dumps({"tier_id": str(tier1.id)}),
            content_type=JSON,
            headers=_auth(fan),
        )
        assert created.status_code == 201
    sub = Subscription.objects.get(fan=fan)
    with override_settings(ENABLE_MOCK_PAYMENT=False):
        res = client.patch(
            f"{BASE}/{sub.id}",
            data=json.dumps({"tier_id": str(tier2.id)}),
            content_type=JSON,
            headers=_auth(fan),
        )
    assert res.status_code == 503
    sub.refresh_from_db()
    assert sub.tier_id == tier1.id


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_subscribe_succeeds_when_mock_enabled(client: Client) -> None:
    """mock on (dev/test) → unchanged: the explicit mock success still works."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier = _tier(creator)
    res = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    assert Subscription.objects.count() == 1
