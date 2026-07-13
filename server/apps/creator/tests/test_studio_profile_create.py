"""Tests for the self-serve creator-page creation endpoint (D4, 크리에이터 되기).

`POST /api/studio/profile` — a signed-in fan opens their own creator page by
claiming a unique handle + display name. "Creator" is derived from operating a
creator profile (handle present on /fan/me), not a separate role.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client

from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

URL = "/api/studio/profile"


def _fan() -> Account:
    """Create a plain fan account."""
    return Account.objects.create(role=Role.FAN.value, nickname="지망생")


def _bearer(account: Account) -> dict[str, str]:
    """Authorization header carrying a fresh access token for ``account``."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _open(client: Client, account: Account, body: dict[str, object]):
    """POST the create-profile body as the given account."""
    return client.post(
        URL,
        data=json.dumps(body),
        content_type="application/json",
        headers=_bearer(account),
    )


def test_requires_auth(client: Client) -> None:
    """An anonymous caller cannot open a creator page."""
    res = client.post(
        URL,
        data=json.dumps({"handle": "mio", "name": "미오"}),
        content_type="application/json",
    )
    assert res.status_code in {401, 403}


def test_fan_opens_creator_page(client: Client) -> None:
    """A fan becomes a creator; /fan/me then carries the new handle."""
    fan = _fan()
    res = _open(client, fan, {"handle": "mio", "name": "미오"})
    assert res.status_code == 201
    body = res.json()
    assert body["handle"] == "mio"
    assert body["name"] == "미오"

    me = client.get("/api/fan/me", headers=_bearer(fan)).json()
    assert me["handle"] == "mio"  # derived creator signal
    assert Creator.objects.filter(owner=fan, handle="mio").exists()


def test_handle_is_lowercased_and_trimmed(client: Client) -> None:
    """The handle/name are normalised (trim + handle lowercased)."""
    fan = _fan()
    res = _open(client, fan, {"handle": "  MiO_01  ", "name": "  미오  "})
    assert res.status_code == 201
    assert res.json()["handle"] == "mio_01"
    assert res.json()["name"] == "미오"


def test_already_a_creator_conflicts(client: Client) -> None:
    """A caller who already operates a creator gets 409, not a second profile."""
    fan = _fan()
    Creator.objects.create(owner=fan, handle="mio", name="미오")
    res = _open(client, fan, {"handle": "another", "name": "또"})
    assert res.status_code == 409
    assert Creator.objects.filter(owner=fan).count() == 1


def test_taken_handle_conflicts(client: Client) -> None:
    """A handle already claimed by another creator is refused (409)."""
    Creator.objects.create(handle="taken", name="선점")
    fan = _fan()
    res = _open(client, fan, {"handle": "taken", "name": "미오"})
    assert res.status_code == 409


def test_reserved_handle_conflicts(client: Client) -> None:
    """A reserved/platform handle cannot be claimed (409)."""
    fan = _fan()
    res = _open(client, fan, {"handle": "admin", "name": "미오"})
    assert res.status_code == 409


def test_invalid_handle_format(client: Client) -> None:
    """A handle with spaces/symbols is rejected (422)."""
    fan = _fan()
    res = _open(client, fan, {"handle": "Mio Space!", "name": "미오"})
    assert res.status_code == 422
