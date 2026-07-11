"""Tests for saved payment methods (R3 — mock tokenization, no PAN stored).

The central assertion is that the card PAN is NEVER persisted or returned: only
brand + last4 + a mock token survive registration. Also covers owner scoping, the
single-primary invariant, and the 503 fail-closed when no tokenizer is wired.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client, override_settings

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.payments.models import SavedPaymentMethod

pytestmark = pytest.mark.django_db

BASE = "/api/fan/payment-methods"
JSON = "application/json"
# A fake (mock) card number — never a real PAN.
_MOCK_PAN = "4111111111111234"


def _fan() -> Account:
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _post(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.post(path, data=json.dumps(body), content_type=JSON, **extra)


def test_requires_auth_401(client: Client) -> None:
    assert client.get(BASE).status_code in {401, 403}


def test_register_stores_only_last4_never_pan(client: Client) -> None:
    fan = _fan()
    res = _post(client, BASE, {"brand": "VISA", "card_number": _MOCK_PAN}, headers=_auth(fan))
    assert res.status_code == 201
    body = res.json()
    assert body["brand"] == "VISA"
    assert body["last4"] == "1234"
    assert body["is_primary"] is True  # the first method is primary
    # The full PAN appears NOWHERE in the response.
    assert _MOCK_PAN not in json.dumps(body)

    method = SavedPaymentMethod.objects.get(id=body["id"])
    assert method.last4 == "1234"
    # The PAN is NEVER stored in any string column of the row.
    for value in (method.brand, method.last4, method.pg_token):
        assert _MOCK_PAN not in value
    # Defensive: the model has no card_number / expiry / cvc attribute at all.
    assert not hasattr(method, "card_number")
    assert not hasattr(method, "expiry")
    assert not hasattr(method, "cvc")


def test_second_method_not_primary_and_set_primary(client: Client) -> None:
    fan = _fan()
    first = _post(
        client, BASE, {"brand": "VISA", "card_number": "4111111111111111"}, headers=_auth(fan)
    ).json()
    second = _post(
        client, BASE, {"brand": "MASTER", "card_number": "5500000000000004"}, headers=_auth(fan)
    ).json()
    assert first["is_primary"] is True
    assert second["is_primary"] is False

    promoted = client.post(f"{BASE}/{second['id']}/primary", headers=_auth(fan))
    assert promoted.status_code == 200
    assert promoted.json()["is_primary"] is True
    # Exactly one primary remains (per-owner partial-unique invariant holds).
    assert SavedPaymentMethod.objects.filter(owner=fan, is_primary=True).count() == 1


def test_list_and_delete_scoped_to_owner(client: Client) -> None:
    fan = _fan()
    other = _fan()
    created = _post(
        client, BASE, {"brand": "VISA", "card_number": "4111111111111111"}, headers=_auth(fan)
    ).json()

    # Another fan sees none of them and cannot delete this one (404, owner-scoped).
    assert client.get(BASE, headers=_auth(other)).json() == []
    assert client.delete(f"{BASE}/{created['id']}", headers=_auth(other)).status_code == 404

    # The owner lists and deletes their own.
    assert len(client.get(BASE, headers=_auth(fan)).json()) == 1
    assert client.delete(f"{BASE}/{created['id']}", headers=_auth(fan)).status_code == 200
    assert not SavedPaymentMethod.objects.filter(id=created["id"]).exists()


def test_non_owner_cannot_set_primary_or_delete_others_method(client: Client) -> None:
    """IDOR regression: fan B cannot set-primary or delete fan A's payment method.

    Both endpoints scope by ``owner=account`` (404 for a stranger, no existence leak);
    this proves a different account is rejected and fan A's method is left untouched.
    """
    fan_a = _fan()
    fan_b = _fan()
    created = _post(
        client, BASE, {"brand": "VISA", "card_number": "4111111111111111"}, headers=_auth(fan_a)
    ).json()
    method_id = created["id"]
    assert created["is_primary"] is True

    # Fan B: set-primary is rejected (404) and changes nothing.
    assert (
        client.post(f"{BASE}/{method_id}/primary", headers=_auth(fan_b)).status_code == 404
    )
    # Fan B: delete is rejected (404) and the row survives.
    assert client.delete(f"{BASE}/{method_id}", headers=_auth(fan_b)).status_code == 404

    method = SavedPaymentMethod.objects.get(id=method_id)
    assert method.owner_id == fan_a.id
    assert method.is_primary is True


@override_settings(ENABLE_MOCK_PAYMENT=False)
def test_register_fails_closed_when_no_tokenizer(client: Client) -> None:
    """With no tokenizer wired (real PG gate), registration returns 503."""
    fan = _fan()
    res = _post(
        client, BASE, {"brand": "VISA", "card_number": "4111111111111111"}, headers=_auth(fan)
    )
    assert res.status_code == 503
    assert SavedPaymentMethod.objects.filter(owner=fan).count() == 0
