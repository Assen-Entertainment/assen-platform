"""Studio (owner) support for ``pricing_kind`` on membership tiers (ASS-297).

The owner studio can mark a tier genuinely free (``pricing_kind="free"``), with a
coherence guard: "free" and a nonzero price are mutually exclusive (422
``PricingFreeRequiresZeroPrice``). An unknown ``pricing_kind`` is a schema 422, and
an omitted value defaults to "paid" (a price-0 row is a placeholder, never free).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client

from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier

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


def test_create_free_tier_with_zero_price_is_201(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(
        client,
        STUDIO,
        {"name": "무료멤버십", "price": 0, "pricing_kind": "free"},
        headers=_auth(owner),
    )
    assert res.status_code == 201
    assert res.json()["pricing_kind"] == "free"
    tier = MembershipTier.objects.get(id=res.json()["id"])
    assert tier.pricing_kind == "free"


def test_create_free_tier_with_nonzero_price_is_422(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(
        client,
        STUDIO,
        {"name": "모순", "price": 5000, "pricing_kind": "free"},
        headers=_auth(owner),
    )
    assert res.status_code == 422
    assert res.json()["code"] == "PricingFreeRequiresZeroPrice"
    assert MembershipTier.objects.count() == 0  # nothing created on the failure


def test_update_paid_tier_to_free_without_zeroing_price_is_422(client: Client) -> None:
    owner, creator = _owner_with_creator()
    tier = MembershipTier.objects.create(creator=creator, name="유료", price=4900)
    res = _patch(
        client, f"{STUDIO}/{tier.id}", {"pricing_kind": "free"}, headers=_auth(owner)
    )
    assert res.status_code == 422
    assert res.json()["code"] == "PricingFreeRequiresZeroPrice"
    tier.refresh_from_db()
    assert tier.pricing_kind == "paid"  # unchanged
    assert tier.price == 4900


def test_update_to_free_and_zero_price_same_patch_is_200(client: Client) -> None:
    owner, creator = _owner_with_creator()
    tier = MembershipTier.objects.create(creator=creator, name="유료", price=4900)
    res = _patch(
        client,
        f"{STUDIO}/{tier.id}",
        {"pricing_kind": "free", "price": 0},
        headers=_auth(owner),
    )
    assert res.status_code == 200
    assert res.json()["pricing_kind"] == "free"
    tier.refresh_from_db()
    assert tier.pricing_kind == "free"
    assert tier.price == 0


def test_create_invalid_pricing_kind_is_422(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(
        client,
        STUDIO,
        {"name": "이상", "price": 0, "pricing_kind": "bogus"},
        headers=_auth(owner),
    )
    assert res.status_code == 422  # schema validation rejects the unknown value
    assert MembershipTier.objects.count() == 0


def test_create_default_pricing_kind_is_paid(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(client, STUDIO, {"name": "기본", "price": 1000}, headers=_auth(owner))
    assert res.status_code == 201
    assert res.json()["pricing_kind"] == "paid"
    tier = MembershipTier.objects.get(id=res.json()["id"])
    assert tier.pricing_kind == "paid"
