"""Locked (membership-gated) product ordering consults subscription (Codex #10).

A ``locked`` product is orderable only by an active subscriber of the product's
creator: a non-subscriber (or a cross-creator subscriber) is refused 422
``MembershipOnlyProduct``, while an active subscriber falls through to a normal
order. Uses digital products so no shipping address is required.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client

from apps.commerce.models import Order, Product
from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus

pytestmark = pytest.mark.django_db

ORDERS = "/api/orders"
JSON = "application/json"


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _fan() -> Account:
    return Account.objects.create(
        role=Role.FAN.value, kyc_status=KycStatus.VERIFIED.value
    )


def _locked_product(creator: Creator) -> Product:
    return Product.objects.create(
        creator=creator, type="digital", title="멤버십 전용", price=1000, locked=True
    )


def _subscribe(fan: Account, creator: Creator) -> None:
    tier = MembershipTier.objects.create(creator=creator, name="스탠다드", price=9900)
    Subscription.objects.create(fan=fan, tier=tier, status=SubscriptionStatus.ACTIVE)


def _order(client: Client, product: Product, account: Account) -> Any:
    return client.post(
        ORDERS,
        data=json.dumps({"product_id": str(product.id)}),
        content_type=JSON,
        headers=_auth(account),
    )


def test_locked_product_rejected_for_non_subscriber(client: Client) -> None:
    """A locked product is refused 422 to a fan with no subscription."""
    product = _locked_product(Creator.objects.create(handle="stellar", name="별빛"))
    res = _order(client, product, _fan())
    assert res.status_code == 422
    assert res.json()["code"] == "MembershipOnlyProduct"
    assert Order.objects.count() == 0


def test_locked_product_ok_for_active_subscriber(client: Client) -> None:
    """An active subscriber of the creator can order the locked product."""
    creator = Creator.objects.create(handle="stellar", name="별빛")
    fan = _fan()
    _subscribe(fan, creator)
    res = _order(client, _locked_product(creator), fan)
    assert res.status_code == 201
    assert Order.objects.count() == 1


def test_locked_product_rejected_for_cross_creator_subscriber(client: Client) -> None:
    """A subscription to a DIFFERENT creator does not unlock this product."""
    fan = _fan()
    _subscribe(fan, Creator.objects.create(handle="other", name="타인"))
    product = _locked_product(Creator.objects.create(handle="stellar", name="별빛"))
    res = _order(client, product, fan)
    assert res.status_code == 422
    assert res.json()["code"] == "MembershipOnlyProduct"
    assert Order.objects.count() == 0
