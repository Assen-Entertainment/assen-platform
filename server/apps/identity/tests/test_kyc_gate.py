"""본인인증 (KYC) interaction gate — cross-app enforcement (대표 07-16).

Product decision: browsing/reading stays open, but any *interaction* (follow, like,
comment, subscribe, order, become-creator) requires the fan to have completed 본인인증
(``Account.kyc_status == VERIFIED``). Verification stays MOCK — ``/fan/verify/confirm``
sets ``kyc_status=VERIFIED`` — so these tests drive the real verify flow and then retry.

Each gated interaction is asserted twice: for an authenticated-but-UNVERIFIED fan it is
refused with 403 ``IdentityVerificationRequired`` and leaves NO side effect (no follow
row, like, comment, subscription, order, or creator profile); after the fan verifies,
the identical call succeeds. Reads (feed / creator detail / store / posts) are asserted
to work for an unverified fan, proving only the write direction is gated.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from django.test import Client

from apps.commerce.models import Order, Product, ProductStatus, ProductType
from apps.content.models import Comment, Like, Post
from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier, Subscription
from apps.social.models import Follow
from config.errors import ErrorCode
from config.payment import PricingKind

pytestmark = pytest.mark.django_db

JSON = "application/json"
VERIFY = "/api/fan/verify/confirm"
_REQUIRED = ErrorCode.IDENTITY_VERIFICATION_REQUIRED.value


# --------------------------------------------------------------------------- #
# Helpers / fixtures
# --------------------------------------------------------------------------- #
def _fan(nickname: str = "미인증팬") -> Account:
    """Create a fan account (defaults to ``kyc_status=unverified``)."""
    return Account.objects.create(role=Role.FAN.value, nickname=nickname)


def _bearer(account: Account) -> dict[str, str]:
    """Authorization header carrying a freshly issued access token for ``account``."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _verify(client: Client, account: Account) -> None:
    """Drive the mock 본인인증 flow so ``account`` becomes VERIFIED, then refresh it."""
    resp = client.post(VERIFY, headers=_bearer(account))
    assert resp.status_code == 200, resp.content
    account.refresh_from_db()
    assert account.kyc_status == KycStatus.VERIFIED.value


def _post(client: Client, path: str, body: dict[str, Any], account: Account) -> Any:
    """POST a JSON body as ``account`` (Ninja parses application/json bodies)."""
    return client.post(
        path, data=json.dumps(body), content_type=JSON, headers=_bearer(account)
    )


def _patch(client: Client, path: str, body: dict[str, Any], account: Account) -> Any:
    """PATCH a JSON body as ``account``."""
    return client.patch(
        path, data=json.dumps(body), content_type=JSON, headers=_bearer(account)
    )


def _assert_gated(resp: Any) -> None:
    """Assert a response is the 본인인증 gate rejection (403 + stable code)."""
    assert resp.status_code == 403, resp.content
    assert resp.json()["code"] == _REQUIRED


def _creator(handle: str = "stellar", *, owner: Account | None = None) -> Creator:
    """Create a published creator."""
    return Creator.objects.create(handle=handle, name="별빛", owner=owner)


def _post_row(creator: Creator) -> Post:
    """Create a public feed post owned by ``creator``."""
    return Post.objects.create(creator=creator, body="본문")


def _paid_tier(creator: Creator, name: str = "골드") -> MembershipTier:
    """Create an active paid membership tier for ``creator``."""
    return MembershipTier.objects.create(
        creator=creator, name=name, price=1000, active=True
    )


def _free_tier(creator: Creator) -> MembershipTier:
    """Create an active free membership tier for ``creator``."""
    return MembershipTier.objects.create(
        creator=creator, name="무료", price=0, active=True, pricing_kind=PricingKind.FREE.value
    )


def _paid_product(creator: Creator) -> Product:
    """Create a selling, digital, paid product (no shipping) owned by ``creator``."""
    return Product.objects.create(
        creator=creator,
        type=ProductType.DIGITAL.value,
        title="디지털 상품",
        price=1000,
        status=ProductStatus.SELLING.value,
    )


def _free_product(creator: Creator) -> Product:
    """Create a selling, digital, free product owned by ``creator``."""
    return Product.objects.create(
        creator=creator,
        type=ProductType.DIGITAL.value,
        title="무료 상품",
        price=0,
        status=ProductStatus.SELLING.value,
        pricing_kind=PricingKind.FREE.value,
    )


# --------------------------------------------------------------------------- #
# social.follow_creator
# --------------------------------------------------------------------------- #
def test_follow_gated_then_allowed(client: Client) -> None:
    """An unverified fan can't follow (403, no edge); after verifying it succeeds."""
    creator = _creator()
    fan = _fan()
    url = f"/api/creators/{creator.handle}/follow"

    gated = client.put(url, headers=_bearer(fan))
    _assert_gated(gated)
    assert Follow.objects.count() == 0

    _verify(client, fan)
    ok = client.put(url, headers=_bearer(fan))
    assert ok.status_code == 200, ok.content
    assert Follow.objects.filter(follower=fan, creator=creator).exists()


# --------------------------------------------------------------------------- #
# content.like_post
# --------------------------------------------------------------------------- #
def test_like_gated_then_allowed(client: Client) -> None:
    """An unverified fan can't like (403, no like row); after verifying it succeeds."""
    post = _post_row(_creator())
    fan = _fan()
    url = f"/api/posts/{post.id}/like"

    gated = client.put(url, headers=_bearer(fan))
    _assert_gated(gated)
    assert Like.objects.count() == 0

    _verify(client, fan)
    ok = client.put(url, headers=_bearer(fan))
    assert ok.status_code == 200, ok.content
    assert Like.objects.filter(post=post, user=fan).exists()


# --------------------------------------------------------------------------- #
# content.create_comment
# --------------------------------------------------------------------------- #
def test_comment_gated_then_allowed(client: Client) -> None:
    """An unverified fan can't comment (403, no comment); after verifying it succeeds."""
    post = _post_row(_creator())
    fan = _fan()
    url = f"/api/posts/{post.id}/comments"

    gated = _post(client, url, {"body": "안녕하세요"}, fan)
    _assert_gated(gated)
    assert Comment.objects.count() == 0

    _verify(client, fan)
    ok = _post(client, url, {"body": "안녕하세요"}, fan)
    assert ok.status_code == 201, ok.content
    assert Comment.objects.filter(post=post, author=fan).exists()


# --------------------------------------------------------------------------- #
# membership.subscribe
# --------------------------------------------------------------------------- #
def test_subscribe_gated_then_allowed(client: Client) -> None:
    """An unverified fan can't subscribe (403, no subscription); verify → succeeds."""
    tier = _paid_tier(_creator())
    fan = _fan()

    gated = _post(client, "/api/subscriptions", {"tier_id": str(tier.id)}, fan)
    _assert_gated(gated)
    assert Subscription.objects.count() == 0

    _verify(client, fan)
    ok = _post(client, "/api/subscriptions", {"tier_id": str(tier.id)}, fan)
    assert ok.status_code == 201, ok.content
    assert Subscription.objects.filter(fan=fan, tier=tier).exists()


# --------------------------------------------------------------------------- #
# membership.subscribe_free
# --------------------------------------------------------------------------- #
def test_subscribe_free_gated_then_allowed(client: Client) -> None:
    """An unverified fan can't join a free tier (403, none); after verifying it works."""
    tier = _free_tier(_creator())
    fan = _fan()

    gated = _post(client, "/api/subscriptions/free", {"tier_id": str(tier.id)}, fan)
    _assert_gated(gated)
    assert Subscription.objects.count() == 0

    _verify(client, fan)
    ok = _post(client, "/api/subscriptions/free", {"tier_id": str(tier.id)}, fan)
    assert ok.status_code == 201, ok.content
    assert Subscription.objects.filter(fan=fan, tier=tier).exists()


# --------------------------------------------------------------------------- #
# membership.change_subscription_tier
# --------------------------------------------------------------------------- #
def test_change_tier_gated_then_allowed(client: Client) -> None:
    """Changing tier is gated: unverified PATCH is 403 before any lookup; verify → 200.

    The gate fires right after the account resolves, so an unverified fan is refused
    even for a subscription id that does not exist (no side effect is possible). After
    verifying, the fan subscribes to one tier and switches to another of the same creator.
    """
    creator = _creator()
    tier_a = _paid_tier(creator, name="실버")
    tier_b = _paid_tier(creator, name="골드")
    fan = _fan()

    gated = _patch(
        client, f"/api/subscriptions/{uuid.uuid4()}", {"tier_id": str(tier_b.id)}, fan
    )
    _assert_gated(gated)
    assert Subscription.objects.count() == 0

    _verify(client, fan)
    created = _post(client, "/api/subscriptions", {"tier_id": str(tier_a.id)}, fan)
    assert created.status_code == 201, created.content
    sub_id = created.json()["id"]
    changed = _patch(
        client, f"/api/subscriptions/{sub_id}", {"tier_id": str(tier_b.id)}, fan
    )
    assert changed.status_code == 200, changed.content
    assert changed.json()["tier_id"] == str(tier_b.id)


# --------------------------------------------------------------------------- #
# commerce.create_order
# --------------------------------------------------------------------------- #
def test_create_order_gated_then_allowed(client: Client) -> None:
    """An unverified fan can't order (403, no order); after verifying it succeeds."""
    product = _paid_product(_creator())
    fan = _fan()

    gated = _post(client, "/api/orders", {"product_id": str(product.id)}, fan)
    _assert_gated(gated)
    assert Order.objects.count() == 0

    _verify(client, fan)
    ok = _post(client, "/api/orders", {"product_id": str(product.id)}, fan)
    assert ok.status_code == 201, ok.content
    assert Order.objects.filter(buyer=fan).exists()


# --------------------------------------------------------------------------- #
# commerce.create_free_order
# --------------------------------------------------------------------------- #
def test_create_free_order_gated_then_allowed(client: Client) -> None:
    """An unverified fan can't grab a free product (403, none); verify → succeeds."""
    product = _free_product(_creator())
    fan = _fan()

    gated = _post(client, "/api/orders/free", {"product_id": str(product.id)}, fan)
    _assert_gated(gated)
    assert Order.objects.count() == 0

    _verify(client, fan)
    ok = _post(client, "/api/orders/free", {"product_id": str(product.id)}, fan)
    assert ok.status_code == 201, ok.content
    assert Order.objects.filter(buyer=fan).exists()


# --------------------------------------------------------------------------- #
# creator.studio_create_profile (become-creator)
# --------------------------------------------------------------------------- #
def test_become_creator_gated_then_allowed(client: Client) -> None:
    """An unverified fan can't become a creator (403, no profile); verify → succeeds."""
    fan = _fan()
    body = {"handle": "newcreator", "name": "새 크리에이터"}

    gated = _post(client, "/api/studio/profile", body, fan)
    _assert_gated(gated)
    assert Creator.objects.count() == 0

    _verify(client, fan)
    ok = _post(client, "/api/studio/profile", body, fan)
    assert ok.status_code == 201, ok.content
    assert Creator.objects.filter(owner=fan).exists()


# --------------------------------------------------------------------------- #
# Reads stay open for an unverified fan
# --------------------------------------------------------------------------- #
def test_reads_work_for_unverified_fan(client: Client) -> None:
    """Browsing/reading surfaces stay open to an authenticated but unverified fan."""
    creator = _creator()
    _post_row(creator)
    _paid_product(creator)
    fan = _fan()
    headers = _bearer(fan)
    assert fan.kyc_status == KycStatus.UNVERIFIED.value

    assert client.get("/api/feed", headers=headers).status_code == 200
    assert client.get("/api/posts", headers=headers).status_code == 200
    assert client.get("/api/products", headers=headers).status_code == 200
    assert (
        client.get(f"/api/creators/{creator.handle}", headers=headers).status_code == 200
    )
