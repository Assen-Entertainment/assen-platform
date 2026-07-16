"""ASS-297 — explicit free-grant flow (membership subscriptions).

A ``pricing_kind=free`` tier is joined ONLY via ``POST /api/subscriptions/free``
(no payment, provenance=free, no billing anchor), never via the paid subscribe,
and a free target is refused on a paid tier change — so a free membership never
auto-converts to paid.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client, override_settings

from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier, Subscription
from apps.payments.models import PaymentAttempt, PaymentProvider
from config.errors import ErrorCode
from config.payment import PaymentProvenance, PricingKind

pytestmark = pytest.mark.django_db

PAID = "/api/subscriptions"
FREE = "/api/subscriptions/free"
JSON = "application/json"


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(
        role=Role.FAN.value, kyc_status=KycStatus.VERIFIED.value
    )


def _auth(account: Account) -> dict[str, str]:
    """Return test-client headers bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _tier(creator: Creator, **kwargs: object) -> MembershipTier:
    """Create a membership tier attached to ``creator``."""
    defaults: dict[str, object] = {"name": "스탠다드", "price": 9900, "period": "월"}
    defaults.update(kwargs)
    return MembershipTier.objects.create(creator=creator, **defaults)


@override_settings(ENABLE_MOCK_PAYMENT=False)
def test_free_subscribe_grants_without_payment(client: Client) -> None:
    """A free tier is joined with the payment gate OFF — no billing anchor, is_free."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier = _tier(creator, pricing_kind=PricingKind.FREE.value, price=0)
    res = client.post(
        FREE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["is_free"] is True
    assert body["next_billing_date"] is None

    sub = Subscription.objects.get(fan=fan)
    assert sub.payment_provenance == PaymentProvenance.FREE
    assert sub.next_billing_date is None
    attempt = PaymentAttempt.objects.get(subscription=sub)
    assert attempt.provider == PaymentProvider.FREE
    assert attempt.authorized_amount == 0


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_free_path_refuses_a_paid_tier(client: Client) -> None:
    """A paid tier (even price 0 placeholder) can't be joined via the free path."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier = _tier(creator, pricing_kind=PricingKind.PAID.value, price=0)
    res = client.post(
        FREE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 422
    assert res.json()["code"] == ErrorCode.PRICING_NOT_FREE.value
    assert Subscription.objects.count() == 0


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_paid_path_refuses_a_free_tier(client: Client) -> None:
    """A free tier can't be joined through the paid subscribe (PricingIsFree)."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier = _tier(creator, pricing_kind=PricingKind.FREE.value, price=0)
    res = client.post(
        PAID,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 422
    assert res.json()["code"] == ErrorCode.PRICING_IS_FREE.value
    assert Subscription.objects.count() == 0


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_change_tier_refuses_a_free_target(client: Client) -> None:
    """A paid subscription can't be switched onto a free tier (no auto-convert)."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    paid = _tier(creator, name="스탠다드", price=9900)
    free = _tier(creator, name="무료", pricing_kind=PricingKind.FREE.value, price=0)
    created = client.post(
        PAID,
        data=json.dumps({"tier_id": str(paid.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert created.status_code == 201
    sub = Subscription.objects.get(fan=fan)
    res = client.patch(
        f"{PAID}/{sub.id}",
        data=json.dumps({"tier_id": str(free.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 422
    assert res.json()["code"] == ErrorCode.PRICING_IS_FREE.value
    sub.refresh_from_db()
    assert sub.tier_id == paid.id


@override_settings(ENABLE_MOCK_PAYMENT=False)
def test_free_subscribe_enforces_one_active_per_creator(client: Client) -> None:
    """The duplicate-active guard holds on the free path too."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier = _tier(creator, pricing_kind=PricingKind.FREE.value, price=0)
    first = client.post(
        FREE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert first.status_code == 201
    second = client.post(
        FREE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert second.status_code == 422
    assert second.json()["code"] == ErrorCode.DUPLICATE_SUBSCRIPTION.value
    assert Subscription.objects.filter(fan=fan).count() == 1
