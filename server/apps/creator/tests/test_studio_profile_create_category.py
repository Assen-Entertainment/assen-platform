"""Tests for the optional category on self-serve creator-page creation (become-creator)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client

from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

URL = "/api/studio/profile"


def _fan() -> Account:
    return Account.objects.create(
        role=Role.FAN.value, nickname="지망생", kyc_status=KycStatus.VERIFIED.value
    )


def _bearer(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _open(client: Client, account: Account, body: dict[str, object]) -> Any:
    return client.post(
        URL, data=json.dumps(body), content_type="application/json", headers=_bearer(account)
    )


def test_open_with_canonical_category_persists(client: Client) -> None:
    """A canonical category chosen at open time is stored on the new creator."""
    fan = _fan()
    res = _open(client, fan, {"handle": "mio", "name": "미오", "category": "버튜버"})
    assert res.status_code == 201
    assert res.json()["category"] == "버튜버"
    assert Creator.objects.get(owner=fan).category == "버튜버"


def test_open_without_category_defaults_blank(client: Client) -> None:
    """Category is optional — omitting it leaves the creator unset (blank)."""
    fan = _fan()
    res = _open(client, fan, {"handle": "mio", "name": "미오"})
    assert res.status_code == 201
    assert res.json()["category"] == ""


def test_open_with_non_canonical_category_422(client: Client) -> None:
    """A non-canonical category rejects the open (422) — no creator is created."""
    fan = _fan()
    res = _open(client, fan, {"handle": "mio", "name": "미오", "category": "굿즈"})
    assert res.status_code == 422
    assert not Creator.objects.filter(owner=fan).exists()
