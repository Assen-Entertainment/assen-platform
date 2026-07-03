"""Smoke test for the seed_demo management command (E11/B1·B4)."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from apps.commerce.models import Product
from apps.creator.models import Creator
from apps.identity.models import Account
from apps.identity.signup_services import hash_phone, normalize_phone
from apps.membership.models import MembershipTier

pytestmark = pytest.mark.django_db


def test_seed_demo_populates_and_is_idempotent() -> None:
    """seed_demo creates the demo graph and re-running does not duplicate."""
    call_command("seed_demo")

    assert Creator.objects.count() == 5
    assert Product.objects.count() == 10
    assert MembershipTier.objects.count() == 3
    # Extended product fields land: one locked, one sold-out listing.
    assert Product.objects.filter(locked=True).count() == 1
    assert Product.objects.filter(sold_out=True).count() == 1
    # The global welcome coupon is seeded (creatorless coupon listing, B7).
    coupon = Product.objects.get(type="coupon")
    assert coupon.creator_id is None
    assert coupon.title == "웰컴 10% 할인 쿠폰"
    # Every creator has an owner account wired.
    assert Creator.objects.filter(owner__isnull=True).count() == 0
    # The demo fan is keyed on the phone-hash so it can log in via mock OTP.
    phone_hash = hash_phone(normalize_phone("010-0000-0001"))
    demo_fan = Account.objects.get(auth_subject_hash=phone_hash)
    assert demo_fan.nickname == "데모팬"

    # Idempotent: a second run keeps the same counts.
    call_command("seed_demo")
    assert Creator.objects.count() == 5
    assert Product.objects.count() == 10
    assert MembershipTier.objects.count() == 3
    assert Account.objects.filter(auth_subject_hash=phone_hash).count() == 1
