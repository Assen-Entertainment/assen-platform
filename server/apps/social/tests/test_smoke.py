"""Smoke + uniqueness tests for the social app (E11/B1)."""

from __future__ import annotations

import pytest
from django.apps import apps
from django.db import IntegrityError

from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.social.models import Follow

pytestmark = pytest.mark.django_db


def test_social_app_installed() -> None:
    """The social app is registered."""
    assert apps.is_installed("apps.social")


def test_follow_is_unique_per_pair() -> None:
    """A fan cannot follow the same creator twice (DB-level uniqueness)."""
    creator = Creator.objects.create(handle="stellar", name="별빛")
    fan = Account.objects.create(role=Role.FAN.value)
    Follow.objects.create(follower=fan, creator=creator)
    with pytest.raises(IntegrityError):
        Follow.objects.create(follower=fan, creator=creator)
