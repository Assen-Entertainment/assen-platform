"""Tests for the account-withdrawal offboarding orchestration (Codex #13).

Withdrawal already anonymises the account and revokes its sessions (see
``test_withdrawal``). This suite covers the *offboarding* it now also performs, all
inside the one withdrawal transaction:

- a creator's storefront is unpublished — the profile 404s to the public reads,
  every product becomes owner-only ``hidden`` (dropped from ``_public_product_qs``,
  so it can no longer be seen or ordered), and every tier is deactivated;
- the withdrawing account's own ACTIVE fan subscriptions are cancelled (no charge),
  while *other* fans' subscriptions to that creator survive;
- the display ``author_name`` snapshot on the account's comments is blanked;
- a staff account is refused at the fan endpoint (403), so it is never withdrawn;
- the whole thing is idempotent, and a plain-fan withdrawal still anonymises +
  revokes exactly as before.
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from apps.commerce.api import _public_product_qs
from apps.commerce.models import Product, ProductStatus, ProductType
from apps.content.models import Comment, Post
from apps.creator.models import Creator
from apps.identity.models import Account, Role, TokenFamily
from apps.identity.services import issue_token_pair, withdraw_account
from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus
from config.errors import ErrorCode

pytestmark = pytest.mark.django_db

_WITHDRAW = "/api/fan/account/withdraw"


def _fan(nickname: str = "미오팬") -> Account:
    """A plain active fan account."""
    return Account.objects.create(role=Role.FAN.value, nickname=nickname)


def _creator(owner: Account | None, handle: str = "mio", name: str = "미오") -> Creator:
    """A published creator profile, optionally owned by ``owner``."""
    return Creator.objects.create(owner=owner, handle=handle, name=name)


def _product(creator: Creator, title: str = "굿즈") -> Product:
    """A publicly-selling product under ``creator``."""
    return Product.objects.create(
        creator=creator, type=ProductType.GOODS.value, title=title, price=1000
    )


def _active_sub(fan: Account, tier: MembershipTier) -> Subscription:
    """An active, renewing subscription (a live billing period)."""
    return Subscription.objects.create(
        fan=fan,
        tier=tier,
        status=SubscriptionStatus.ACTIVE.value,
        current_period_end=timezone.now() + timedelta(days=30),
    )


def _bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def _post_json(client: Client, path: str, **extra: Any) -> Any:
    return client.post(path, data=json.dumps({}), content_type="application/json", **extra)


def test_creator_withdrawal_unpublishes_profile_and_hides_storefront(
    client: Client,
) -> None:
    """A withdrawing creator's profile unpublishes and their storefront goes dark."""
    owner = _fan("크리에이터")
    creator = _creator(owner)
    p1 = _product(creator, "티셔츠")
    p2 = _product(creator, "스티커")
    tier = MembershipTier.objects.create(creator=creator, name="골드", price=9900)

    withdraw_account(owner)

    creator.refresh_from_db()
    assert creator.published is False
    # Both products are now owner-only hidden, so a consumer can neither see nor
    # order them (the order flow gates through the same _public_product_qs funnel).
    for product in (p1, p2):
        product.refresh_from_db()
        assert product.status == ProductStatus.HIDDEN.value
        assert not _public_product_qs(None).filter(id=product.id).exists()
    # The tier is deactivated, so the subscribe path (active=True only) rejects it.
    tier.refresh_from_db()
    assert tier.active is False
    # The public profile read now 404s just like an unknown handle (no existence leak).
    assert client.get(f"/api/creators/{creator.handle}").status_code == 404


def test_withdrawal_cancels_own_active_subscriptions_without_charging() -> None:
    """The fan's own ACTIVE subs are cancelled immediately; no settlement is taken."""
    fan = _fan()
    other = _creator(_fan("다른크리에이터"), handle="other", name="다른")
    tier = MembershipTier.objects.create(creator=other, name="스탠다드", price=5000)
    sub = _active_sub(fan, tier)

    withdraw_account(fan)

    sub.refresh_from_db()
    assert sub.status == SubscriptionStatus.CANCELLED.value
    assert sub.cancelled_at is not None
    # Cancelled rows leave the billing worker's ACTIVE-only candidate set, so the
    # withdrawal never re-bills the gone member (no charge).
    assert not Subscription.objects.filter(
        fan=fan, status=SubscriptionStatus.ACTIVE.value
    ).exists()


def test_withdrawal_leaves_other_fans_subscriptions_to_the_creator_intact() -> None:
    """Unpublishing a creator does not cancel *subscribers'* memberships to them."""
    owner = _fan("크리에이터")
    creator = _creator(owner)
    tier = MembershipTier.objects.create(creator=creator, name="골드", price=9900)
    subscriber = _fan("구독자")
    other_sub = _active_sub(subscriber, tier)

    withdraw_account(owner)

    # Only the *withdrawing* account's own subs are cancelled — a different fan's
    # active membership to the (now unpublished) creator is untouched.
    other_sub.refresh_from_db()
    assert other_sub.status == SubscriptionStatus.ACTIVE.value
    assert other_sub.cancelled_at is None


def test_withdrawal_blanks_comment_author_name_snapshots() -> None:
    """The denormalised display name on the account's comments is pseudonymised."""
    author = _fan("작성자")
    creator = _creator(_fan("포스트주인"), handle="poster", name="포스터")
    post = Post.objects.create(creator=creator, body="본문")
    comment = Comment.objects.create(
        post=post, author=author, author_name="작성자", body="댓글"
    )

    withdraw_account(author)

    comment.refresh_from_db()
    assert comment.author_name == ""
    # The author FK is kept for linkage under the now-pseudonymous id (not deleted).
    assert comment.author_id == author.id


def test_staff_account_cannot_withdraw_via_fan_endpoint(client: Client) -> None:
    """A staff account is refused (403) and is not withdrawn (last-admin invariant)."""
    staff = Account.objects.create(role=Role.ADMIN.value, nickname="관리자")
    pair = issue_token_pair(staff)

    resp = _post_json(client, _WITHDRAW, headers=_bearer(pair.access_token))

    assert resp.status_code == 403
    assert resp.json()["code"] == ErrorCode.STAFF_WITHDRAWAL_FORBIDDEN.value
    staff.refresh_from_db()
    assert staff.withdrawn_at is None
    assert staff.is_active is True


def test_withdrawal_is_idempotent_second_call_noops() -> None:
    """A second withdrawal short-circuits on withdrawn_at and changes nothing."""
    owner = _fan("크리에이터")
    creator = _creator(owner)
    product = _product(creator)
    withdraw_account(owner)

    owner.refresh_from_db()
    first_ts = owner.withdrawn_at
    creator.refresh_from_db()
    assert creator.published is False

    withdraw_account(owner)  # already withdrawn → no-op

    owner.refresh_from_db()
    assert owner.withdrawn_at == first_ts
    product.refresh_from_db()
    assert product.status == ProductStatus.HIDDEN.value


def test_plain_fan_withdrawal_still_anonymises_and_revokes() -> None:
    """Regression: a fan with no creator/subs is anonymised + fully revoked as before."""
    fan = _fan("평범한팬")
    fan.auth_subject_hash = "somehash"
    fan.save(update_fields=["auth_subject_hash"])
    issue_token_pair(fan)  # a live session that must be cut off

    withdraw_account(fan)

    fan.refresh_from_db()
    assert fan.nickname == ""
    assert fan.auth_subject_hash == ""
    assert fan.is_active is False
    assert fan.withdrawn_at is not None
    assert not TokenFamily.objects.filter(account=fan, revoked=False).exists()
