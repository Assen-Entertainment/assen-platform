"""Tests for the membership studio (owner tier write) + public active filter (R3)."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
from django.test import Client

from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus

pytestmark = pytest.mark.django_db

STUDIO = "/api/studio/tiers"
JSON = "application/json"


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _owner_with_creator(handle: str = "stellar") -> tuple[Account, Creator]:
    account = Account.objects.create(role=Role.FAN.value)
    creator = Creator.objects.create(handle=handle, name="별빛", owner=account)
    return account, creator


def _post(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.post(path, data=json.dumps(body), content_type=JSON, **extra)


def _patch(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.patch(path, data=json.dumps(body), content_type=JSON, **extra)


def test_tier_studio_requires_auth_401(client: Client) -> None:
    assert client.get(STUDIO).status_code in {401, 403}


def test_tier_studio_requires_creator_owner_403(client: Client) -> None:
    fan = Account.objects.create(role=Role.FAN.value)
    assert client.get(STUDIO, headers=_auth(fan)).status_code == 403
    assert (
        _post(client, STUDIO, {"name": "라이트", "price": 4900}, headers=_auth(fan)).status_code
        == 403
    )


def test_tier_create_patch_delete(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    created = _post(
        client, STUDIO, {"name": "라이트", "price": 4900, "benefits": ["A"]}, headers=_auth(owner)
    )
    assert created.status_code == 201
    tier_id = created.json()["id"]
    assert created.json()["active"] is True

    patched = _patch(
        client, f"{STUDIO}/{tier_id}", {"active": False, "price": 5900}, headers=_auth(owner)
    )
    assert patched.status_code == 200
    assert patched.json()["active"] is False
    assert patched.json()["price"] == 5900

    deleted = client.delete(f"{STUDIO}/{tier_id}", headers=_auth(owner))
    assert deleted.status_code == 200
    assert not MembershipTier.objects.filter(id=tier_id).exists()


def test_public_tiers_exclude_inactive(client: Client) -> None:
    _owner, creator = _owner_with_creator()
    MembershipTier.objects.create(creator=creator, name="활성", price=4900, active=True)
    MembershipTier.objects.create(creator=creator, name="비활성", price=9900, active=False)
    names = {t["name"] for t in client.get("/api/tiers").json()}
    assert "활성" in names
    assert "비활성" not in names


def test_tier_patch_scoped_to_owner_is_404(client: Client) -> None:
    _owner, creator = _owner_with_creator()
    other = Account.objects.create(role=Role.FAN.value)
    Creator.objects.create(handle="other", name="다른", owner=other)
    tier = MembershipTier.objects.create(creator=creator, name="라이트", price=4900)
    assert (
        _patch(client, f"{STUDIO}/{tier.id}", {"price": 1}, headers=_auth(other)).status_code
        == 404
    )


def test_non_owner_cannot_delete_others_tier(client: Client) -> None:
    """IDOR regression: another creator cannot delete a tier they do not own.

    ``studio_delete_tier`` scopes by ``creator=_owner_creator(account)``, so a
    different creator gets 404 (no existence leak); this proves the stranger is
    rejected and the tier survives.
    """
    _owner, creator = _owner_with_creator("stellar")
    other = Account.objects.create(role=Role.FAN.value)
    Creator.objects.create(handle="other", name="다른", owner=other)
    tier = MembershipTier.objects.create(creator=creator, name="라이트", price=4900)

    assert client.delete(f"{STUDIO}/{tier.id}", headers=_auth(other)).status_code == 404
    assert MembershipTier.objects.filter(id=tier.id).exists()


def test_studio_list_tiers_subscribers_counts_active_only(client: Client) -> None:
    """``subscribers`` (ASS-264) = active-status subscriptions; cancelled excluded."""
    owner, creator = _owner_with_creator()
    tier = MembershipTier.objects.create(creator=creator, name="베이직", price=4900)
    Subscription.objects.create(
        fan=Account.objects.create(role=Role.FAN.value), tier=tier, next_billing_date=date.today()
    )
    Subscription.objects.create(
        fan=Account.objects.create(role=Role.FAN.value), tier=tier, next_billing_date=date.today()
    )
    Subscription.objects.create(
        fan=Account.objects.create(role=Role.FAN.value),
        tier=tier,
        next_billing_date=date.today(),
        status=SubscriptionStatus.CANCELLED.value,
    )

    listed = client.get(STUDIO, headers=_auth(owner)).json()
    row = next(t for t in listed if t["id"] == str(tier.id))
    assert row["subscribers"] == 2


def test_studio_new_tier_subscribers_is_zero(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    created = _post(client, STUDIO, {"name": "새티어", "price": 1000}, headers=_auth(owner))
    assert created.json()["subscribers"] == 0


def test_studio_list_tiers_subscribers_isolated_from_other_owner(client: Client) -> None:
    """Another creator's subscribers never leak into this owner's tier counts."""
    owner, creator = _owner_with_creator("stellar")
    _other_owner, other_creator = _owner_with_creator("nova")
    my_tier = MembershipTier.objects.create(creator=creator, name="내티어", price=1000)
    other_tier = MembershipTier.objects.create(creator=other_creator, name="타인티어", price=1000)
    Subscription.objects.create(
        fan=Account.objects.create(role=Role.FAN.value),
        tier=other_tier,
        next_billing_date=date.today(),
    )

    listed = client.get(STUDIO, headers=_auth(owner)).json()
    assert {t["id"] for t in listed} == {str(my_tier.id)}
    assert listed[0]["subscribers"] == 0
