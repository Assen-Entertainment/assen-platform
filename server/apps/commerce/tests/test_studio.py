"""Tests for the commerce studio (owner catalog write) + public 19+/visibility gate.

Covers owner-guard 403 / auth 401, create+list including draft/status, owner-scoped
update/delete (404 for a non-owner), and the consumer ``list_products`` excluding
draft/hidden and gated adult (R3 gated features).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client, override_settings

from apps.commerce.models import Product
from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

STUDIO = "/api/studio/products"
JSON = "application/json"


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _owner_with_creator(handle: str = "stellar") -> tuple[Account, Creator]:
    account = Account.objects.create(role=Role.FAN.value)
    creator = Creator.objects.create(handle=handle, name="별빛", owner=account)
    return account, creator


def _post(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.post(path, data=json.dumps(body), content_type=JSON, **extra)


def _patch(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.patch(path, data=json.dumps(body), content_type=JSON, **extra)


def test_studio_requires_auth_401(client: Client) -> None:
    assert client.get(STUDIO).status_code in {401, 403}


def test_studio_requires_creator_owner_403(client: Client) -> None:
    fan = Account.objects.create(role=Role.FAN.value)  # operates no creator
    assert client.get(STUDIO, headers=_auth(fan)).status_code == 403
    res = _post(
        client, STUDIO, {"type": "goods", "title": "x", "price": 1000}, headers=_auth(fan)
    )
    assert res.status_code == 403


def test_studio_create_and_owner_list_includes_draft(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(
        client,
        STUDIO,
        {"type": "goods", "title": "굿즈", "price": 15000, "status": "draft"},
        headers=_auth(owner),
    )
    assert res.status_code == 201
    assert res.json()["status"] == "draft"
    listed = client.get(STUDIO, headers=_auth(owner)).json()
    assert any(p["status"] == "draft" for p in listed)


def test_studio_create_invalid_type_is_422(client: Client) -> None:
    owner, _creator = _owner_with_creator()
    res = _post(
        client, STUDIO, {"type": "bogus", "title": "x", "price": 0}, headers=_auth(owner)
    )
    assert res.status_code == 422


def test_public_list_excludes_draft_and_hidden(client: Client) -> None:
    _owner, creator = _owner_with_creator()
    for title, status in (("공개", "selling"), ("초안", "draft"), ("숨김", "hidden")):
        Product.objects.create(
            creator=creator, type="goods", title=title, price=1000, status=status
        )
    titles = {p["title"] for p in client.get("/api/products").json()["items"]}
    assert "공개" in titles
    assert "초안" not in titles
    assert "숨김" not in titles


@override_settings(ENABLE_ADULT_CONTENT=False)
def test_public_list_excludes_adult_when_flag_off(client: Client) -> None:
    _owner, creator = _owner_with_creator()
    Product.objects.create(
        creator=creator, type="goods", title="성인", price=1000, adult_only=True
    )
    titles = {p["title"] for p in client.get("/api/products").json()["items"]}
    assert "성인" not in titles


@override_settings(ENABLE_ADULT_CONTENT=True)
def test_public_list_shows_adult_only_to_verified(client: Client) -> None:
    _owner, creator = _owner_with_creator()
    Product.objects.create(
        creator=creator, type="goods", title="성인", price=1000, adult_only=True
    )
    verified = Account.objects.create(
        role=Role.FAN.value, adult_verified=True, kyc_status=KycStatus.VERIFIED.value
    )
    listed = client.get("/api/products", headers=_auth(verified)).json()["items"]
    shown = {r["title"] for r in listed}
    assert "성인" in shown
    # Anonymous still sees nothing.
    assert "성인" not in {p["title"] for p in client.get("/api/products").json()["items"]}


def test_studio_update_and_delete_scoped_to_owner(client: Client) -> None:
    owner, creator = _owner_with_creator()
    other = Account.objects.create(role=Role.FAN.value)
    Creator.objects.create(handle="other", name="다른", owner=other)
    prod = Product.objects.create(creator=creator, type="goods", title="원본", price=1000)

    # A different creator-owner cannot patch/delete it (404, owner-scoped).
    assert (
        _patch(client, f"{STUDIO}/{prod.id}", {"title": "해킹"}, headers=_auth(other)).status_code
        == 404
    )
    assert client.delete(f"{STUDIO}/{prod.id}", headers=_auth(other)).status_code == 404

    # The owner can update and then delete.
    patched = _patch(
        client, f"{STUDIO}/{prod.id}", {"title": "수정", "status": "hidden"}, headers=_auth(owner)
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "수정"
    assert patched.json()["status"] == "hidden"
    deleted = client.delete(f"{STUDIO}/{prod.id}", headers=_auth(owner))
    assert deleted.status_code == 200
    assert not Product.objects.filter(id=prod.id).exists()
