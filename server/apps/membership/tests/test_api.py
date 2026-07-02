"""Tests for the membership read API — tier catalog (E11/B2)."""

from __future__ import annotations

import pytest
from django.apps import apps
from django.test import Client

from apps.creator.models import Creator
from apps.membership.models import MembershipTier

pytestmark = pytest.mark.django_db

BASE = "/api/tiers"


def test_membership_app_installed() -> None:
    """The membership app is registered."""
    assert apps.is_installed("apps.membership")


def test_tiers_list_ordered_and_filtered(client: Client) -> None:
    """Tiers return as a plain list ordered by sort_order; creator filter works."""
    creator = Creator.objects.create(handle="stellar", name="별빛")
    MembershipTier.objects.create(
        creator=creator, name="스탠다드", price=9900, benefits=["b"], featured=True, sort_order=1
    )
    MembershipTier.objects.create(
        creator=creator, name="라이트", price=4900, benefits=["a"], sort_order=0
    )

    res = client.get(BASE)
    assert res.status_code == 200
    tiers = res.json()
    assert [t["name"] for t in tiers] == ["라이트", "스탠다드"]
    assert tiers[1]["featured"] is True
    assert tiers[0]["benefits"] == ["a"]

    scoped = client.get(f"{BASE}?creator_id={creator.id}").json()
    assert len(scoped) == 2
