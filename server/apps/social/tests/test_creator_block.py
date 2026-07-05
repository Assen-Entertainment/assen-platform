"""Tests for fan personal creator-block (ASS-226, R4-W3).

Symmetric to ``content/tests/test_adult_gating.py``: a fan who blocks a creator has
that creator hidden from their OWN aggregate surfaces (feed, discovery, search,
global posts), while a non-blocking fan and an anonymous viewer still see them.
Explicit single navigation is deliberately NOT hidden — ``get_creator`` and a
``?creator_id=`` post list return the blocked creator and carry a ``blocked`` flag
so the web can render the block state (a personal block is not existence hiding,
unlike the 19+ gate). Blocking auto-unfollows and is idempotent.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from django.test import Client

from apps.commerce.models import Product
from apps.content.models import Post
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.membership.models import MembershipTier
from apps.social.models import CreatorBlock, Follow

pytestmark = pytest.mark.django_db

BLOCKS = "/api/fan/blocks"


def _creator(handle: str = "stellar", name: str = "별빛") -> Creator:
    return Creator.objects.create(handle=handle, name=name)


def _fan(nickname: str = "팬") -> Account:
    return Account.objects.create(role=Role.FAN.value, nickname=nickname)


def _bearer(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _block(client: Client, account: Account, creator: Creator) -> Any:
    return client.post(
        BLOCKS,
        data=json.dumps({"creator_id": str(creator.id)}),
        content_type="application/json",
        headers=_bearer(account),
    )


def _ids(resp: Any) -> set[str]:
    return {row["id"] for row in resp.json()["items"]}


def _handles(resp: Any) -> set[str]:
    return {row["handle"] for row in resp.json()["items"]}


# --------------------------------------------------------------------------- #
# Mutations: block / unblock / list
# --------------------------------------------------------------------------- #
def test_block_creates_edge_and_auto_unfollows(client: Client) -> None:
    """POST blocks the creator and auto-unfollows an existing follow (standard UX)."""
    fan = _fan()
    creator = _creator()
    Follow.objects.create(follower=fan, creator=creator)
    resp = _block(client, fan, creator)
    assert resp.status_code == 200
    assert resp.json() == {"blocked": True, "creator_id": str(creator.id)}
    assert CreatorBlock.objects.filter(blocker=fan, creator=creator).exists()
    # Auto-unfollow: the follow edge is gone after a block.
    assert not Follow.objects.filter(follower=fan, creator=creator).exists()


def test_block_is_idempotent(client: Client) -> None:
    """A second block is a no-op (still 200, single edge)."""
    fan = _fan()
    creator = _creator()
    first = _block(client, fan, creator)
    second = _block(client, fan, creator)
    assert first.status_code == second.status_code == 200
    assert CreatorBlock.objects.filter(blocker=fan, creator=creator).count() == 1


def test_block_unknown_creator_is_404_with_code(client: Client) -> None:
    """Blocking an unknown creator id 404s with the stable ``BlockTargetNotFound`` code."""
    fan = _fan()
    resp = client.post(
        BLOCKS,
        data=json.dumps({"creator_id": str(uuid.uuid4())}),
        content_type="application/json",
        headers=_bearer(fan),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "BlockTargetNotFound"
    assert CreatorBlock.objects.count() == 0


def test_unblock_removes_edge_and_is_idempotent(client: Client) -> None:
    """DELETE removes the block; unblocking a non-block is still 200 (idempotent)."""
    fan = _fan()
    creator = _creator()
    _block(client, fan, creator)

    gone = client.delete(f"{BLOCKS}/{creator.id}", headers=_bearer(fan))
    assert gone.status_code == 200
    assert gone.json() == {"blocked": False, "creator_id": str(creator.id)}
    assert not CreatorBlock.objects.filter(blocker=fan, creator=creator).exists()

    again = client.delete(f"{BLOCKS}/{creator.id}", headers=_bearer(fan))
    assert again.status_code == 200


def test_block_requires_auth(client: Client) -> None:
    """An unauthenticated block is rejected; no edge created."""
    creator = _creator()
    resp = client.post(
        BLOCKS,
        data=json.dumps({"creator_id": str(creator.id)}),
        content_type="application/json",
    )
    assert resp.status_code in {401, 403}
    assert CreatorBlock.objects.count() == 0


def test_list_blocks_returns_only_own_blocked_creators(client: Client) -> None:
    """GET lists the caller's blocked creators; another fan's blocks don't leak in."""
    fan = _fan()
    other = _fan("다른팬")
    a = _creator("aaa", "에이")
    b = _creator("bbb", "비")
    c = _creator("ccc", "시")
    _block(client, fan, a)
    _block(client, fan, b)
    _block(client, other, c)

    rows = client.get(BLOCKS, headers=_bearer(fan)).json()
    assert {r["handle"] for r in rows} == {"aaa", "bbb"}
    assert all({"creator_id", "name", "handle"} <= set(r) for r in rows)


# --------------------------------------------------------------------------- #
# Gating: aggregate surfaces exclude, single navigation does not (blocker-only)
# --------------------------------------------------------------------------- #
def test_feed_excludes_blocked_for_blocker_only(client: Client) -> None:
    """Feed hides a blocked creator's posts for the blocker; others/anon see them."""
    fan = _fan()
    other = _fan("다른팬")
    blocked = _creator("blocked", "차단대상")
    shown = _creator("shown", "노출크리")
    p_blocked = Post.objects.create(creator=blocked, body="숨김")
    p_shown = Post.objects.create(creator=shown, body="노출")
    _block(client, fan, blocked)

    blocker_ids = _ids(client.get("/api/feed", headers=_bearer(fan)))
    assert str(p_shown.id) in blocker_ids
    assert str(p_blocked.id) not in blocker_ids
    # A different fan (no block) sees both.
    assert {str(p_shown.id), str(p_blocked.id)} <= _ids(
        client.get("/api/feed", headers=_bearer(other))
    )
    # Anonymous sees both — a personal block never affects an anonymous read.
    assert {str(p_shown.id), str(p_blocked.id)} <= _ids(client.get("/api/feed"))


def test_global_posts_exclude_blocked_but_profile_visit_does_not(client: Client) -> None:
    """Global /posts hides the blocked creator; ?creator_id= and single fetch do not."""
    fan = _fan()
    blocked = _creator("blocked", "차단")
    post = Post.objects.create(creator=blocked, body="글")
    _block(client, fan, blocked)

    # Global aggregate list hides it.
    assert str(post.id) not in _ids(client.get("/api/posts", headers=_bearer(fan)))
    # Explicit profile visit (?creator_id=) returns it (web renders block UI).
    scoped = client.get(f"/api/posts?creator_id={blocked.id}", headers=_bearer(fan))
    assert str(post.id) in _ids(scoped)
    # Explicit single-post navigation is not hidden either.
    assert client.get(f"/api/posts/{post.id}", headers=_bearer(fan)).status_code == 200


def test_discovery_excludes_blocked_for_blocker_only(client: Client) -> None:
    """The /creators discovery list hides a blocked creator for the blocker only."""
    fan = _fan()
    _creator("blocked", "차단")
    _creator("shown", "노출")
    creator_blocked = Creator.objects.get(handle="blocked")
    _block(client, fan, creator_blocked)

    blocker_handles = _handles(client.get("/api/creators", headers=_bearer(fan)))
    assert "shown" in blocker_handles
    assert "blocked" not in blocker_handles
    # Anonymous discovery still shows both.
    assert {"shown", "blocked"} <= _handles(client.get("/api/creators"))


def test_get_creator_single_not_hidden_and_flags_blocked(client: Client) -> None:
    """Single creator fetch is returned (not hidden) and carries the ``blocked`` flag."""
    fan = _fan()
    other = _fan("다른팬")
    creator = _creator("stellar", "별빛")
    _block(client, fan, creator)

    blocker_view = client.get("/api/creators/stellar", headers=_bearer(fan))
    assert blocker_view.status_code == 200
    assert blocker_view.json()["blocked"] is True
    # A non-blocking fan and an anonymous viewer see blocked=False (isolated per user).
    assert client.get("/api/creators/stellar", headers=_bearer(other)).json()["blocked"] is False
    assert client.get("/api/creators/stellar").json()["blocked"] is False


def test_search_excludes_blocked_creator_and_their_products(client: Client) -> None:
    """Search hides a blocked creator AND their products for the blocker; anon sees both."""
    fan = _fan()
    blocked = _creator("neonbeats", "Neon Beats")
    Product.objects.create(creator=blocked, type="goods", title="네온 굿즈", price=1000)
    _block(client, fan, blocked)

    creator_hits = client.get("/api/search?q=Neon", headers=_bearer(fan)).json()
    assert all(c["handle"] != "neonbeats" for c in creator_hits["creators"])
    product_hits = client.get("/api/search?q=네온", headers=_bearer(fan)).json()
    assert all(p["title"] != "네온 굿즈" for p in product_hits["products"])

    # Anonymous search still finds both the creator and their product.
    anon_creators = client.get("/api/search?q=Neon").json()
    assert any(c["handle"] == "neonbeats" for c in anon_creators["creators"])
    anon_products = client.get("/api/search?q=네온").json()
    assert any(p["title"] == "네온 굿즈" for p in anon_products["products"])


def test_global_catalog_excludes_blocked_but_store_visit_and_single_fetch_do_not(
    client: Client,
) -> None:
    """Global /products hides a blocked creator's catalog; ?creator_id= and single fetch don't.

    Mirrors ``test_global_posts_exclude_blocked_but_profile_visit_does_not``: the
    unfiltered browse is the aggregate surface (blocker-only exclusion), while
    explicit creator-scoped navigation (a store visit) and a direct single-product
    fetch are unaffected — a personal block is not existence hiding.
    """
    fan = _fan()
    other = _fan("다른팬")
    blocked = _creator("blocked", "차단")
    product = Product.objects.create(creator=blocked, type="goods", title="차단상품", price=1000)

    global_before = client.get("/api/products", headers=_bearer(fan))
    assert str(product.id) in _ids(global_before)

    _block(client, fan, blocked)

    # Global aggregate browse hides it for the blocker only.
    assert str(product.id) not in _ids(client.get("/api/products", headers=_bearer(fan)))
    assert str(product.id) in _ids(client.get("/api/products", headers=_bearer(other)))
    assert str(product.id) in _ids(client.get("/api/products"))

    # Explicit store visit (?creator_id=) returns it even for the blocker.
    scoped = client.get(f"/api/products?creator_id={blocked.id}", headers=_bearer(fan))
    assert str(product.id) in _ids(scoped)

    # Explicit single-product navigation is not hidden either.
    single = client.get(f"/api/products/{product.id}", headers=_bearer(fan))
    assert single.status_code == 200


def test_unblock_restores_visibility(client: Client) -> None:
    """After unblocking, the creator reappears on the blocker's aggregate surfaces."""
    fan = _fan()
    blocked = _creator("blocked", "차단")
    post = Post.objects.create(creator=blocked, body="글")
    _block(client, fan, blocked)
    assert str(post.id) not in _ids(client.get("/api/feed", headers=_bearer(fan)))

    client.delete(f"{BLOCKS}/{blocked.id}", headers=_bearer(fan))
    assert str(post.id) in _ids(client.get("/api/feed", headers=_bearer(fan)))
    assert "blocked" in _handles(client.get("/api/creators", headers=_bearer(fan)))


# --------------------------------------------------------------------------- #
# Write-interaction guard (F4): no new like/comment/order against a blocked creator;
# direct reads stay allowed. Unblocking restores the interaction.
# --------------------------------------------------------------------------- #
def test_like_on_blocked_creator_post_is_422_and_unblock_restores(client: Client) -> None:
    """A blocked creator's post can be *read* but not liked (422); unblock re-allows it."""
    fan = _fan()
    blocked = _creator("blocked", "차단")
    post = Post.objects.create(creator=blocked, body="글")
    _block(client, fan, blocked)

    # Direct single read is still allowed (a personal block is not existence hiding).
    assert client.get(f"/api/posts/{post.id}", headers=_bearer(fan)).status_code == 200

    liked = client.put(f"/api/posts/{post.id}/like", headers=_bearer(fan))
    assert liked.status_code == 422
    assert liked.json()["code"] == "InteractionBlocked"

    # Unblock → the like now succeeds.
    client.delete(f"{BLOCKS}/{blocked.id}", headers=_bearer(fan))
    reliked = client.put(f"/api/posts/{post.id}/like", headers=_bearer(fan))
    assert reliked.status_code == 200
    assert reliked.json()["liked"] is True


def test_comment_on_blocked_creator_post_is_422_and_unblock_restores(client: Client) -> None:
    """A comment on a blocked creator's post is refused (422); unblock re-allows it."""
    fan = _fan()
    blocked = _creator("blocked", "차단")
    post = Post.objects.create(creator=blocked, body="글")
    _block(client, fan, blocked)

    body = json.dumps({"body": "댓글"})
    blocked_resp = client.post(
        f"/api/posts/{post.id}/comments",
        data=body,
        content_type="application/json",
        headers=_bearer(fan),
    )
    assert blocked_resp.status_code == 422
    assert blocked_resp.json()["code"] == "InteractionBlocked"

    client.delete(f"{BLOCKS}/{blocked.id}", headers=_bearer(fan))
    ok = client.post(
        f"/api/posts/{post.id}/comments",
        data=body,
        content_type="application/json",
        headers=_bearer(fan),
    )
    assert ok.status_code == 201


def test_order_of_blocked_creator_product_is_422_and_unblock_restores(client: Client) -> None:
    """Ordering a blocked creator's product is refused (422); unblock re-allows it."""
    fan = _fan()
    blocked = _creator("blocked", "차단")
    product = Product.objects.create(
        creator=blocked, type="goods", title="차단상품", price=1000
    )
    _block(client, fan, blocked)

    # The catalog single read is still allowed.
    assert client.get(f"/api/products/{product.id}", headers=_bearer(fan)).status_code == 200

    order = client.post(
        "/api/orders",
        data=json.dumps({"product_id": str(product.id)}),
        content_type="application/json",
        headers=_bearer(fan),
    )
    assert order.status_code == 422
    assert order.json()["code"] == "InteractionBlocked"

    client.delete(f"{BLOCKS}/{blocked.id}", headers=_bearer(fan))
    reorder = client.post(
        "/api/orders",
        data=json.dumps({"product_id": str(product.id)}),
        content_type="application/json",
        headers=_bearer(fan),
    )
    assert reorder.status_code == 201


# --------------------------------------------------------------------------- #
# Membership /tiers global-browse gating (F8): the 6th aggregate surface.
# --------------------------------------------------------------------------- #
def test_global_tiers_exclude_blocked_but_explicit_creator_id_does_not(client: Client) -> None:
    """Global /tiers hides a blocked creator's tier; ?creator_id= and anon do not."""
    fan = _fan()
    blocked = _creator("blocked", "차단")
    shown = _creator("shown", "노출")
    t_blocked = MembershipTier.objects.create(creator=blocked, name="차단등급", price=9900)
    t_shown = MembershipTier.objects.create(creator=shown, name="노출등급", price=9900)
    _block(client, fan, blocked)

    def _tier_ids(resp: Any) -> set[str]:
        return {row["id"] for row in resp.json()}

    # Global (unfiltered) browse excludes the blocked creator's tier for the blocker.
    global_ids = _tier_ids(client.get("/api/tiers", headers=_bearer(fan)))
    assert str(t_shown.id) in global_ids
    assert str(t_blocked.id) not in global_ids

    # Explicit ?creator_id= visit is not hidden (creator-scoped navigation).
    scoped = client.get(f"/api/tiers?creator_id={blocked.id}", headers=_bearer(fan))
    assert str(t_blocked.id) in _tier_ids(scoped)

    # Anonymous browse is unaffected — a personal block never touches an anon read.
    assert str(t_blocked.id) in _tier_ids(client.get("/api/tiers"))
