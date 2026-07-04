"""Tests for the creator studio profile edit (owner guard) (R3)."""

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


def _patch(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.patch(path, data=json.dumps(body), content_type=JSON, **extra)


def test_profile_requires_auth_401(client: Client) -> None:
    assert _patch(client, PROFILE, {"name": "x"}).status_code in {401, 403}


def test_profile_requires_creator_403(client: Client) -> None:
    fan = Account.objects.create(role=Role.FAN.value)  # operates no creator
    assert _patch(client, PROFILE, {"name": "x"}, headers=_auth(fan)).status_code == 403


def test_profile_updates_own_creator(client: Client) -> None:
    account = Account.objects.create(role=Role.FAN.value)
    Creator.objects.create(handle="stellar", name="별빛", owner=account)
    res = _patch(
        client,
        PROFILE,
        {"name": "새이름", "bio": "소개", "category": "일러스트"},
        headers=_auth(account),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "새이름"
    assert body["bio"] == "소개"
    assert body["category"] == "일러스트"
    assert body["handle"] == "stellar"  # handle is not changed here


def test_profile_partial_update_leaves_other_fields(client: Client) -> None:
    account = Account.objects.create(role=Role.FAN.value)
    Creator.objects.create(handle="stellar", name="별빛", bio="원래 소개", owner=account)
    res = _patch(client, PROFILE, {"category": "뮤직"}, headers=_auth(account))
    assert res.status_code == 200
    body = res.json()
    assert body["category"] == "뮤직"
    assert body["bio"] == "원래 소개"  # untouched
    assert body["name"] == "별빛"  # untouched
