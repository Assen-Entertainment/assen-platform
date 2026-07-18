"""Tests for the studio dashboard stats endpoint (owner real counts) (R4-W5).

Covers owner-scoped count accuracy (followers/posts/products/orders/subscribers),
the OwnerRequired 403 (with its stable ``code``) for a non-owner, auth gating,
cross-creator isolation, the empty-state zero baseline, and that a cancelled
order is excluded from the ``orders`` count. Counts only — the endpoint never
exposes a monetary/settlement figure (that is gated, ASS-229).
"""

from __future__ import annotations

from datetime import date

import pytest
from django.test import Client

from apps.commerce.models import Order, OrderItem, OrderStatus, Product, ProductStatus
from apps.content.models import Post
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus
from apps.social.models import Follow

pytestmark = pytest.mark.django_db

STATS = "/api/studio/stats"

_ZERO = {
    "followers": 0,
    "posts": 0,
    "products": 0,
    "products_selling": 0,
    "orders": 0,
    "subscribers": 0,
}


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _fan() -> Account:
    return Account.objects.create(role=Role.FAN.value)


def _owner_with_creator(handle: str = "stellar") -> tuple[Account, Creator]:
    account = _fan()
    creator = Creator.objects.create(handle=handle, name="별빛", owner=account)
    return account, creator


def _order_with_items(buyer: Account, *products: Product) -> Order:
    """A keyless order snapshotting one line per given product."""
    order = Order.objects.create(buyer=buyer)
    for p in products:
        OrderItem.objects.create(
            order=order, product=p, title=p.title, item_type=p.type, qty=1, price=p.price
        )
    return order


def test_stats_requires_auth_401(client: Client) -> None:
    assert client.get(STATS).status_code in {401, 403}


def test_stats_requires_creator_owner_403(client: Client) -> None:
    fan = _fan()  # operates no creator
    res = client.get(STATS, headers=_auth(fan))
    assert res.status_code == 403
    body = res.json()
    assert body["code"] == "OwnerRequired"
    assert body["detail"]


def test_stats_empty_creator_all_zero(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    assert client.get(STATS, headers=_auth(owner)).json() == _ZERO


def test_stats_counts_are_accurate(client: Client) -> None:
    owner, creator = _owner_with_creator()

    # 2 followers.
    Follow.objects.create(follower=_fan(), creator=creator)
    Follow.objects.create(follower=_fan(), creator=creator)

    # 3 posts.
    for _ in range(3):
        Post.objects.create(creator=creator, body="hi")

    # 3 products, 2 of them selling (a draft must be excluded from products_selling).
    selling_a = Product.objects.create(creator=creator, type="goods", title="A", price=1000)
    selling_b = Product.objects.create(creator=creator, type="digital", title="B", price=2000)
    Product.objects.create(
        creator=creator, type="goods", title="C", price=500, status=ProductStatus.DRAFT.value
    )

    # 2 distinct orders that include the creator's products. The first order holds
    # two of the creator's items but must count once (OrderItem -> distinct Order).
    buyer = _fan()
    _order_with_items(buyer, selling_a, selling_b)
    _order_with_items(buyer, selling_a)

    # 2 active subscribers; a cancelled subscription must be excluded.
    tier = MembershipTier.objects.create(creator=creator, name="베이직")
    Subscription.objects.create(fan=_fan(), tier=tier, next_billing_date=date.today())
    Subscription.objects.create(fan=_fan(), tier=tier, next_billing_date=date.today())
    Subscription.objects.create(
        fan=_fan(),
        tier=tier,
        next_billing_date=date.today(),
        status=SubscriptionStatus.CANCELLED.value,
    )

    assert client.get(STATS, headers=_auth(owner)).json() == {
        "followers": 2,
        "posts": 3,
        "products": 3,
        "products_selling": 2,
        "orders": 2,
        "subscribers": 2,
    }


def test_stats_orders_excludes_cancelled(client: Client) -> None:
    owner, creator = _owner_with_creator()
    product = Product.objects.create(creator=creator, type="goods", title="A", price=1000)
    buyer = _fan()

    _order_with_items(buyer, product)  # valid order (default status: paid)
    cancelled = _order_with_items(buyer, product)
    cancelled.status = OrderStatus.CANCELLED.value
    cancelled.save(update_fields=["status"])

    body = client.get(STATS, headers=_auth(owner)).json()
    assert body["orders"] == 1  # the cancelled order does not count


def test_stats_isolated_from_other_creator(client: Client) -> None:
    owner, _creator = _owner_with_creator("stellar")
    _other_owner, other = _owner_with_creator("nova")

    # Load the OTHER creator with data across every counted relation.
    Follow.objects.create(follower=_fan(), creator=other)
    Post.objects.create(creator=other, body="x")
    other_product = Product.objects.create(creator=other, type="goods", title="X", price=100)
    _order_with_items(_fan(), other_product)
    other_tier = MembershipTier.objects.create(creator=other, name="X")
    Subscription.objects.create(fan=_fan(), tier=other_tier, next_billing_date=date.today())

    # The owner (with no data of their own) still sees all zeros — no leakage.
    assert client.get(STATS, headers=_auth(owner)).json() == _ZERO
