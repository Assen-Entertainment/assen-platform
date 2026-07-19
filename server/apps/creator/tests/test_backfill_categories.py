"""Tests for the backfill_creator_categories management command."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from apps.creator.models import Creator

pytestmark = pytest.mark.django_db


def test_backfills_known_handle_and_is_idempotent() -> None:
    """A known blank-category creator (e2ecreator) gets its canonical category once."""
    Creator.objects.create(handle="e2ecreator", name="E2E Seed Creator")
    call_command("backfill_creator_categories")
    creator = Creator.objects.get(handle="e2ecreator")
    assert creator.category == "버튜버"

    # Idempotent: a second run leaves the (now non-blank) category untouched.
    call_command("backfill_creator_categories")
    assert Creator.objects.get(handle="e2ecreator").category == "버튜버"


def test_never_overwrites_an_existing_category() -> None:
    """A creator who already has a category is left alone (blank-only backfill)."""
    Creator.objects.create(handle="stellar", name="별빛", category="뮤직")
    call_command("backfill_creator_categories")
    assert Creator.objects.get(handle="stellar").category == "뮤직"


def test_unknown_handle_untouched_without_default_all() -> None:
    """An unknown blank creator stays blank unless --default-all is passed."""
    Creator.objects.create(handle="somebodynew", name="신인")
    call_command("backfill_creator_categories")
    assert Creator.objects.get(handle="somebodynew").category == ""

    call_command("backfill_creator_categories", "--default-all")
    assert Creator.objects.get(handle="somebodynew").category == "일러스트"
