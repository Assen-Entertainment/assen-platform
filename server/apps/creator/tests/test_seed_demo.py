"""Smoke test for the seed_demo management command (E11/B1·B4)."""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.commerce.models import Product
from apps.creator.models import Creator
from apps.identity.models import Account
from apps.identity.signup_services import hash_phone, normalize_phone
from apps.membership.models import MembershipTier

pytestmark = pytest.mark.django_db


def test_seed_demo_populates_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """seed_demo creates the demo graph and re-running does not duplicate."""
    monkeypatch.setenv("ALLOW_DEMO_SEED", "1")  # explicit opt-in (ASS-288)
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


def test_seed_demo_refused_without_optin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without ALLOW_DEMO_SEED=1 the command refuses and writes nothing (ASS-288)."""
    monkeypatch.delenv("ALLOW_DEMO_SEED", raising=False)
    with pytest.raises(CommandError, match="ALLOW_DEMO_SEED"):
        call_command("seed_demo")
    assert Creator.objects.count() == 0


@override_settings(ENABLE_MOCK_FAN_OTP=False)
def test_seed_demo_refused_on_prod_like_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A prod-like (mocks off) profile is refused even with the opt-in (ASS-288)."""
    monkeypatch.setenv("ALLOW_DEMO_SEED", "1")
    with pytest.raises(CommandError, match="prod-like"):
        call_command("seed_demo")
    assert Creator.objects.count() == 0
