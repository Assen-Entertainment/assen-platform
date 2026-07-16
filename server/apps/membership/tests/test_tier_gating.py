"""Tier gating regressions: inactive-tier subscribe + active-subscription delete guard.

Codex R3 MAJOR #3: subscribing to an inactive/archived tier must 404 (no existence
leak), mirroring ``list_tiers``' active filter. code-reviewer #5: deleting a tier
CASCADEs its subscriptions, so a tier with an active subscription can't be deleted
(422) — the owner soft-archives (``active=False``) instead.
"""

from __future__ import annotations

import json
from datetime import date

import pytest
from django.test import Client

from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus

pytestmark = pytest.mark.django_db

SUBSCRIPTIONS = "/api/subscriptions"
STUDIO = "/api/studio/tiers"
JSON = "application/json"


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _fan() -> Account:
    return Account.objects.create(
        role=Role.FAN.value, kyc_status=KycStatus.VERIFIED.value
    )


def _owner_with_creator(handle: str = "stellar") -> tuple[Account, Creator]:
    account = Account.objects.create(
        role=Role.FAN.value, kyc_status=KycStatus.VERIFIED.value
    )
    creator = Creator.objects.create(handle=handle, name="별빛", owner=account)
    return account, creator


# --- subscribe to inactive tier (Codex MAJOR #3) ----------------------------- #


def test_subscribe_inactive_tier_is_404(client: Client) -> None:
    """An inactive/archived tier is not subscribable — 404 (no existence leak)."""
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier = MembershipTier.objects.create(
        creator=creator, name="비활성", price=9900, active=False
    )
    res = client.post(
        SUBSCRIPTIONS,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(_fan()),
    )
    assert res.status_code == 404
    assert Subscription.objects.count() == 0


def test_subscribe_active_tier_still_succeeds(client: Client) -> None:
    """An active tier remains subscribable (no regression to the smoke path)."""
    creator = Creator.objects.create(handle="stellar", name="별빛")
    tier = MembershipTier.objects.create(creator=creator, name="스탠다드", price=9900)
    res = client.post(
        SUBSCRIPTIONS,
        data=json.dumps({"tier_id": str(tier.id)}),
        content_type=JSON,
        headers=_auth(_fan()),
    )
    assert res.status_code == 201


# --- delete tier with active subscription (code-reviewer #5) ----------------- #


def test_delete_tier_with_active_subscription_is_422(client: Client) -> None:
    """A tier with a live subscription can't be deleted; the owner soft-archives instead."""
    owner, creator = _owner_with_creator()
    tier = MembershipTier.objects.create(creator=creator, name="스탠다드", price=9900)
    Subscription.objects.create(
        fan=_fan(),
        tier=tier,
        status=SubscriptionStatus.ACTIVE,
        next_billing_date=date.today(),
    )
    res = client.delete(f"{STUDIO}/{tier.id}", headers=_auth(owner))
    assert res.status_code == 422
    assert MembershipTier.objects.filter(id=tier.id).exists()  # not destroyed


def test_delete_tier_without_active_subscription_ok(client: Client) -> None:
    """A tier with no active subscription deletes normally (200)."""
    owner, creator = _owner_with_creator()
    tier = MembershipTier.objects.create(creator=creator, name="스탠다드", price=9900)
    res = client.delete(f"{STUDIO}/{tier.id}", headers=_auth(owner))
    assert res.status_code == 200
    assert not MembershipTier.objects.filter(id=tier.id).exists()


def test_delete_tier_with_only_cancelled_subscription_ok(client: Client) -> None:
    """A cancelled (non-active) subscription does not block deletion."""
    owner, creator = _owner_with_creator()
    tier = MembershipTier.objects.create(creator=creator, name="스탠다드", price=9900)
    Subscription.objects.create(
        fan=_fan(),
        tier=tier,
        status=SubscriptionStatus.CANCELLED,
        next_billing_date=date.today(),
    )
    res = client.delete(f"{STUDIO}/{tier.id}", headers=_auth(owner))
    assert res.status_code == 200
    assert not MembershipTier.objects.filter(id=tier.id).exists()
