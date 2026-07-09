"""Tests for the creator read API, search, and the demo seed (E11/B2)."""

from __future__ import annotations

import pytest
from django.apps import apps
from django.core.management import call_command
from django.test import Client

from apps.commerce.models import Product
from apps.content.models import Post
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.social.models import Follow

pytestmark = pytest.mark.django_db

BASE = "/api/creators"


def _creator(handle: str, name: str = "크리에이터", **extra: object) -> Creator:
    """Create a creator with the given handle."""
    return Creator.objects.create(handle=handle, name=name, **extra)


def _bearer(account: Account) -> dict[str, str]:
    """Authorization header carrying a freshly issued access token for ``account``."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def test_creator_app_installed() -> None:
    """The creator app is registered."""
    assert apps.is_installed("apps.creator")


def test_list_creators_page(client: Client) -> None:
    """The list endpoint returns a page with both creators and no next cursor."""
    _creator("stellar", name="별빛")
    _creator("neonbeats", name="네온")
    res = client.get(BASE)
    assert res.status_code == 200
    body = res.json()
    assert {c["handle"] for c in body["items"]} == {"stellar", "neonbeats"}
    assert body["next_cursor"] is None
    row = body["items"][0]
    assert {"id", "handle", "name", "followers", "posts", "following", "accent_color"}.issubset(row)


def test_get_creator_by_handle_and_404(client: Client) -> None:
    """A known handle returns 200 with fields; an unknown handle returns 404."""
    _creator("stellar", name="별빛", accent_color="#E14B8A", verified=True)
    ok = client.get(f"{BASE}/stellar")
    assert ok.status_code == 200
    assert ok.json()["handle"] == "stellar"
    assert ok.json()["accent_color"] == "#E14B8A"
    assert client.get(f"{BASE}/nope").status_code == 404


def test_counts_are_derived(client: Client) -> None:
    """Follower/post counts are derived from the social/content relations."""
    creator = _creator("stellar")
    Post.objects.create(creator=creator, body="a")
    Post.objects.create(creator=creator, body="b")
    fan = Account.objects.create(role=Role.FAN.value)
    Follow.objects.create(follower=fan, creator=creator)
    body = client.get(f"{BASE}/stellar").json()
    assert body["posts"] == 2
    assert body["followers"] == 1


def test_counts_stay_independent_with_many_followers_and_posts(client: Client) -> None:
    """Follower and post counts do not multiply each other (subquery, not join fan-out).

    With F followers and P posts a two-relation join produces F×P intermediate rows;
    the per-relation subquery counts must report F and P exactly, so this pins that
    they stay independent (a fan-out bug would surface as F×P or a collapsed value).
    """
    creator = _creator("stellar")
    for i in range(3):
        Post.objects.create(creator=creator, body=f"post-{i}")
    for _ in range(4):
        Follow.objects.create(follower=Account.objects.create(role=Role.FAN.value), creator=creator)
    body = client.get(f"{BASE}/stellar").json()
    assert body["posts"] == 3
    assert body["followers"] == 4

    # A creator with neither relation reports 0/0 (Coalesce of the empty subquery),
    # and it does not leak the other creator's counts.
    _creator("lonely")
    other = client.get(f"{BASE}/lonely").json()
    assert other["posts"] == 0
    assert other["followers"] == 0


def test_pagination_cursor(client: Client) -> None:
    """A limit produces a cursor; following it returns the remainder."""
    for handle in ("a", "b", "c"):
        _creator(handle)
    first = client.get(f"{BASE}?limit=2").json()
    assert len(first["items"]) == 2
    assert first["next_cursor"]
    second = client.get(f"{BASE}?limit=2&cursor={first['next_cursor']}").json()
    assert len(second["items"]) == 1
    assert second["next_cursor"] is None


def test_search(client: Client) -> None:
    """Search matches creators by name/handle and products by title."""
    _creator("neonbeats", name="Neon Beats")
    stellar = _creator("stellar", name="별빛")
    Product.objects.create(creator=stellar, type="goods", title="아크릴 스탠드", price=18000)
    creators = client.get("/api/search?q=Neon").json()
    assert any(x["handle"] == "neonbeats" for x in creators["creators"])
    products = client.get("/api/search?q=아크릴").json()
    assert any(x["title"] == "아크릴 스탠드" for x in products["products"])
    assert client.get("/api/search?q=").json() == {
        "creators": [],
        "products": [],
        "next_offset": None,
    }


def test_search_ranks_and_broadens_fields(client: Client) -> None:
    """Search also matches bio/category and ranks exact/prefix name hits first."""
    _creator("aaa", name="루미", bio="일러스트레이터")  # exact name
    _creator("bbb", name="루미나", category="음악")  # name prefix of the query
    _creator("ccc", name="별", bio="루미를 좋아함")  # bio-only match
    res = client.get("/api/search?q=루미").json()
    handles = [c["handle"] for c in res["creators"]]
    assert set(handles) == {"aaa", "bbb", "ccc"}  # all match (name/bio)
    assert handles.index("aaa") < handles.index("ccc")  # exact name ranks above bio


def test_search_paginates_with_offset(client: Client) -> None:
    """limit/offset page the ranked results and next_offset signals a further page."""
    for i in range(3):
        _creator(f"star{i}", name=f"스타{i}")
    first = client.get("/api/search?q=스타&limit=2").json()
    assert len(first["creators"]) == 2
    assert first["next_offset"] == 2
    second = client.get("/api/search?q=스타&limit=2&offset=2").json()
    assert len(second["creators"]) == 1
    assert second["next_offset"] is None


def test_list_creators_recommendation_sorts(client: Client) -> None:
    """sort=popular ranks by real follower count; ranked surfaces are one bounded page."""
    _creator("a", name="A")
    b = _creator("b", name="B")
    for _ in range(2):
        Follow.objects.create(
            follower=Account.objects.create(role=Role.FAN.value), creator=b
        )
    Follow.objects.create(
        follower=Account.objects.create(role=Role.FAN.value), creator=_creator("c")
    )
    popular = client.get(f"{BASE}?sort=popular").json()
    handles = [c["handle"] for c in popular["items"]]
    assert handles[0] == "b"  # most-followed first (real count, not a proxy)
    assert popular["next_cursor"] is None  # ranked surface = single bounded page
    # an unknown sort falls back to the default handle-ordered cursor page
    default = client.get(f"{BASE}?sort=bogus").json()
    assert [c["handle"] for c in default["items"]] == ["a", "b", "c"]


def test_following_flag_is_false_for_anonymous(client: Client) -> None:
    """An anonymous read never breaks and always reports ``following`` False."""
    creator = _creator("stellar")
    Follow.objects.create(follower=Account.objects.create(role=Role.FAN.value), creator=creator)
    assert client.get(f"{BASE}/stellar").json()["following"] is False
    assert client.get(BASE).json()["items"][0]["following"] is False


def test_following_flag_is_true_for_the_follower(client: Client) -> None:
    """An authenticated read reflects the caller's own follow (detail + list)."""
    creator = _creator("stellar")
    fan = Account.objects.create(role=Role.FAN.value, nickname="미오팬")
    Follow.objects.create(follower=fan, creator=creator)
    headers = _bearer(fan)

    assert client.get(f"{BASE}/stellar", headers=headers).json()["following"] is True
    row = next(
        c for c in client.get(BASE, headers=headers).json()["items"] if c["handle"] == "stellar"
    )
    assert row["following"] is True


def test_following_flag_is_isolated_per_user(client: Client) -> None:
    """One fan's follow does not surface as another fan's ``following``."""
    creator = _creator("stellar")
    Follow.objects.create(follower=Account.objects.create(role=Role.FAN.value), creator=creator)
    other = Account.objects.create(role=Role.FAN.value, nickname="다른팬")
    assert client.get(f"{BASE}/stellar", headers=_bearer(other)).json()["following"] is False


def test_handle_rejects_non_slug() -> None:
    """A non-slug handle (slash/space/uppercase) fails model validation."""
    from django.core.exceptions import ValidationError

    for bad in ("foo/bar", "foo bar", "Foo"):
        with pytest.raises(ValidationError):
            Creator(handle=bad, name="x").full_clean()


def test_seed_demo_creators_are_listable(client: Client) -> None:
    """After seeding, the creator list endpoint serves the five demo creators.

    The seed *counts*/idempotency are asserted in ``creator/tests/test_seed_demo.py``
    (the canonical seed smoke, B7); this only guards that seeded creators surface
    through the read API.
    """
    call_command("seed_demo")
    assert len(client.get(BASE).json()["items"]) == 5
