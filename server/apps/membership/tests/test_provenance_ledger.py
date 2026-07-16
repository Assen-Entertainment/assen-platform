"""ASS-298 — payment provenance + ledger (membership).

A mock subscription (and a mock tier change) records ``payment_provenance=mock``
and ledgers a succeeded MOCK :class:`PaymentAttempt` linked to the subscription
(and to no order). A tier change is a fresh settlement, so it writes a second
attempt at the new tier's price.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client, override_settings

from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier, Subscription
from apps.payments.models import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentProvider,
)
from config.payment import PaymentProvenance

pytestmark = pytest.mark.django_db

BASE = "/api/subscriptions"
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


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_subscribe_records_mock_provenance_and_ledger(client: Client) -> None:
    """A mock subscribe is tagged ``mock`` and ledgers one succeeded attempt."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier = _tier(creator, price=9900)
    res = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    sub = Subscription.objects.get(fan=fan)
    assert sub.payment_provenance == PaymentProvenance.MOCK

    attempts = list(PaymentAttempt.objects.filter(subscription=sub))
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt.provider == PaymentProvider.MOCK
    assert attempt.status == PaymentAttemptStatus.SUCCEEDED
    assert attempt.authorized_amount == tier.price
    assert attempt.currency == "KRW"
    assert attempt.order_id is None


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_change_tier_refreshes_provenance_and_ledgers_again(client: Client) -> None:
    """A mock tier change keeps ``mock`` provenance and writes a second attempt."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier1 = _tier(creator, name="스탠다드", price=9900)
    tier2 = _tier(creator, name="프리미엄", price=19900)
    created = client.post(
        BASE,
        data=json.dumps({"tier_id": str(tier1.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert created.status_code == 201
    sub = Subscription.objects.get(fan=fan)

    res = client.patch(
        f"{BASE}/{sub.id}",
        data=json.dumps({"tier_id": str(tier2.id)}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 200
    sub.refresh_from_db()
    assert sub.tier_id == tier2.id
    assert sub.payment_provenance == PaymentProvenance.MOCK

    attempts = list(
        PaymentAttempt.objects.filter(subscription=sub).order_by("created_at")
    )
    assert len(attempts) == 2
    assert attempts[1].authorized_amount == tier2.price
    assert attempts[1].provider == PaymentProvider.MOCK
