"""Tests for creator category validation on the studio profile edit (PATCH)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client

from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

PROFILE = "/api/studio/profile"
JSON = "application/json"


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _patch(client: Client, body: dict[str, object], **extra: Any) -> Any:
    return client.patch(PROFILE, data=json.dumps(body), content_type=JSON, **extra)


def test_sets_canonical_category(client: Client) -> None:
    """A canonical category is accepted and persisted."""
    account = Account.objects.create(role=Role.FAN.value)
    Creator.objects.create(handle="stellar", name="별빛", owner=account)
    res = _patch(client, {"category": "버튜버"}, headers=_auth(account))
    assert res.status_code == 200
    assert res.json()["category"] == "버튜버"
    assert Creator.objects.get(handle="stellar").category == "버튜버"


def test_rejects_non_canonical_category_422(client: Client) -> None:
    """A category outside the canonical set is a 422 and is not persisted."""
    account = Account.objects.create(role=Role.FAN.value)
    Creator.objects.create(handle="stellar", name="별빛", category="일러스트", owner=account)
    res = _patch(client, {"category": "굿즈"}, headers=_auth(account))
    assert res.status_code == 422
    assert Creator.objects.get(handle="stellar").category == "일러스트"  # unchanged


def test_allows_clearing_category_with_empty_string(client: Client) -> None:
    """The empty string clears the category (unset) — always allowed."""
    account = Account.objects.create(role=Role.FAN.value)
    Creator.objects.create(handle="stellar", name="별빛", category="일러스트", owner=account)
    res = _patch(client, {"category": ""}, headers=_auth(account))
    assert res.status_code == 200
    assert res.json()["category"] == ""
