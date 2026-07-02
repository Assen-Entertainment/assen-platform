"""Tests for the commerce read API — product catalog (E11/B2)."""

from __future__ import annotations

import pytest
from django.apps import apps
from django.test import Client

from apps.commerce.models import Product
from apps.creator.models import Creator

pytestmark = pytest.mark.django_db

BASE = "/api/products"


def test_commerce_app_installed() -> None:
    """The commerce app is registered."""
    assert apps.is_installed("apps.commerce")


def test_products_list_and_filters(client: Client) -> None:
    """Listing returns all products; creator/type filters narrow the set."""
    creator = Creator.objects.create(handle="stellar", name="별빛")
    Product.objects.create(
        creator=creator, type="goods", title="아크릴 스탠드", price=18000, meta="한정"
    )
    Product.objects.create(creator=None, type="digital", title="화보집", price=9900)

    everything = client.get(BASE).json()
    assert len(everything["items"]) == 2
    assert everything["next_cursor"] is None

    by_creator = client.get(f"{BASE}?creator_id={creator.id}").json()
    assert len(by_creator["items"]) == 1
    assert by_creator["items"][0]["title"] == "아크릴 스탠드"
    assert by_creator["items"][0]["price"] == 18000

    by_type = client.get(f"{BASE}?product_type=digital").json()
    assert len(by_type["items"]) == 1
    assert by_type["items"][0]["title"] == "화보집"
