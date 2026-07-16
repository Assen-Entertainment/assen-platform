"""Entitlement service tests — active_subscription + can_view_post (Codex #10).

Server-authoritative membership access: a public post is open to everyone, while a
``members`` post is gated behind an active subscription whose tier matches
``required_tier`` (NULL = any active sub). Fail closed for anonymous viewers.
"""

from __future__ import annotations

import pytest

from apps.content.models import Post, PostVisibility
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus
from apps.membership.services import active_subscription, can_view_post

pytestmark = pytest.mark.django_db


def _creator(**kwargs: object) -> Creator:
    """Create a creator (defaults to @stellar)."""
    defaults: dict[str, object] = {"handle": "stellar", "name": "별빛"}
    defaults.update(kwargs)
    return Creator.objects.create(**defaults)


def _tier(creator: Creator, **kwargs: object) -> MembershipTier:
    """Create a membership tier for ``creator``."""
    defaults: dict[str, object] = {"name": "스탠다드", "price": 9900}
    defaults.update(kwargs)
    return MembershipTier.objects.create(creator=creator, **defaults)


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def _subscribe(
    fan: Account,
    tier: MembershipTier,
    status: str = SubscriptionStatus.ACTIVE.value,
) -> Subscription:
    """Create a subscription (creator is pinned from the tier on save)."""
    return Subscription.objects.create(fan=fan, tier=tier, status=status)


def _members_post(creator: Creator, **kwargs: object) -> Post:
    """Create a members-only post."""
    return Post.objects.create(
        creator=creator, visibility=PostVisibility.MEMBERS.value, **kwargs
    )


def test_public_post_visible_to_anonymous() -> None:
    """A public post is readable by an anonymous (None) viewer."""
    post = Post.objects.create(
        creator=_creator(), body="공개", visibility=PostVisibility.PUBLIC.value
    )
    assert can_view_post(None, post) is True


def test_members_post_hidden_from_anonymous() -> None:
    """A members post is fail-closed for an anonymous viewer."""
    assert can_view_post(None, _members_post(_creator(), body="멤버십")) is False


def test_members_post_hidden_from_cancelled_subscriber() -> None:
    """A cancelled subscription grants no entitlement."""
    creator = _creator()
    fan = _fan()
    _subscribe(fan, _tier(creator), status=SubscriptionStatus.CANCELLED.value)
    assert active_subscription(fan, creator) is None
    assert can_view_post(fan, _members_post(creator, body="멤버십")) is False


def test_members_post_hidden_from_wrong_tier_subscriber() -> None:
    """A required-tier post is hidden from a subscriber holding a different tier."""
    creator = _creator()
    light = _tier(creator, name="라이트", sort_order=0)
    premium = _tier(creator, name="프리미엄", sort_order=1)
    fan = _fan()
    _subscribe(fan, light)
    post = _members_post(creator, body="프리미엄 전용", required_tier=premium)
    assert can_view_post(fan, post) is False


def test_members_post_visible_to_matching_subscriber() -> None:
    """A required-tier post is visible to a subscriber holding exactly that tier."""
    creator = _creator()
    premium = _tier(creator, name="프리미엄")
    fan = _fan()
    sub = _subscribe(fan, premium)
    post = _members_post(creator, body="프리미엄 전용", required_tier=premium)
    assert active_subscription(fan, creator) == sub
    assert can_view_post(fan, post) is True


def test_members_post_visible_to_any_active_sub_when_no_required_tier() -> None:
    """A NULL required_tier post is unlocked by any active subscription."""
    creator = _creator()
    fan = _fan()
    _subscribe(fan, _tier(creator))
    assert can_view_post(fan, _members_post(creator, body="멤버십")) is True


def test_members_post_visible_to_own_creator_owner() -> None:
    """The post's own creator/owner always sees their gated post (no sub needed)."""
    owner = _fan()
    creator = _creator(owner=owner)
    assert can_view_post(owner, _members_post(creator, body="멤버십")) is True


def test_members_post_visible_to_operator() -> None:
    """A staff/operator account may view a gated post (moderation)."""
    operator = Account.objects.create(role=Role.OPERATOR.value)
    assert can_view_post(operator, _members_post(_creator(), body="멤버십")) is True


def test_cross_creator_subscription_does_not_grant_access() -> None:
    """A subscription to one creator does not unlock another creator's gated post."""
    creator_a = _creator(handle="alpha", name="알파")
    creator_b = _creator(handle="beta", name="베타")
    fan = _fan()
    _subscribe(fan, _tier(creator_a))
    post_b = _members_post(creator_b, body="B 멤버십")
    assert active_subscription(fan, creator_b) is None
    assert can_view_post(fan, post_b) is False
