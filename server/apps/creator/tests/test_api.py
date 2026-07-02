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
from apps.social.models import Follow

pytestmark = pytest.mark.django_db

BASE = "/api/creators"


def _creator(handle: str, name: str = "크리에이터", **extra: object) -> Creator:
    """Create a creator with the given handle."""
    return Creator.objects.create(handle=handle, name=name, **extra)


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
    assert client.get("/api/search?q=").json() == {"creators": [], "products": []}


def test_handle_rejects_non_slug() -> None:
    """A non-slug handle (slash/space/uppercase) fails model validation."""
    from django.core.exceptions import ValidationError

    for bad in ("foo/bar", "foo bar", "Foo"):
        with pytest.raises(ValidationError):
            Creator(handle=bad, name="x").full_clean()


def test_seed_demo_is_idempotent(client: Client) -> None:
    """Running the seed twice yields the same fixed counts."""
    call_command("seed_demo")
    call_command("seed_demo")
    assert Creator.objects.count() == 5
    assert Post.objects.count() == 6
    stellar = Creator.objects.get(handle="stellar")
    assert stellar.products.count() == 4
    assert stellar.tiers.count() == 3
    assert len(client.get(BASE).json()["items"]) == 5
