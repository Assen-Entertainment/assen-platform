"""Payment-method robustness regressions (Codex R3 MAJOR #4 + code-reviewer #7).

Covers the invalid-card 422 branch (``PaymentError`` when the card carries fewer
than four digits) and the single-primary invariant that the atomic + row-lock swap
in ``set_primary_payment_method`` protects. True concurrency can't be exercised on
the in-memory sqlite test DB, so the swap is verified functionally (the invariant
holds across repeated switches) plus a direct DB-constraint test documenting the
partial-unique the code guards.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.db import IntegrityError, transaction
from django.test import Client

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.payments.models import SavedPaymentMethod

pytestmark = pytest.mark.django_db

BASE = "/api/fan/payment-methods"
JSON = "application/json"


def _fan() -> Account:
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _post(client: Client, path: str, body: dict[str, object], **extra: Any) -> Any:
    return client.post(path, data=json.dumps(body), content_type=JSON, **extra)


# --- invalid card → 422 (code-reviewer #7) ----------------------------------- #


def test_register_card_with_too_few_digits_is_422(client: Client) -> None:
    """A card number carrying fewer than 4 digits fails tokenization (PaymentError → 422)."""
    fan = _fan()
    # 4 chars satisfy the schema min_length, but zero digits fail the tokenizer.
    res = _post(client, BASE, {"brand": "VISA", "card_number": "abcd"}, headers=_auth(fan))
    assert res.status_code == 422
    assert res.json()["detail"] == "카드 정보가 올바르지 않아요."
    assert SavedPaymentMethod.objects.filter(owner=fan).count() == 0


# --- set_primary single-primary invariant (Codex MAJOR #4) ------------------- #


def test_set_primary_keeps_single_primary_across_switches(client: Client) -> None:
    """Switching primary across methods always leaves exactly one primary for the owner."""
    fan = _fan()
    a = _post(
        client, BASE, {"brand": "VISA", "card_number": "4111111111111111"}, headers=_auth(fan)
    ).json()
    b = _post(
        client, BASE, {"brand": "MASTER", "card_number": "5500000000000004"}, headers=_auth(fan)
    ).json()
    c = _post(
        client, BASE, {"brand": "AMEX", "card_number": "340000000000009"}, headers=_auth(fan)
    ).json()
    assert a["is_primary"] is True and b["is_primary"] is False and c["is_primary"] is False

    for target in (b, c, a, b):
        res = client.post(f"{BASE}/{target['id']}/primary", headers=_auth(fan))
        assert res.status_code == 200
        assert res.json()["is_primary"] is True
        primaries = SavedPaymentMethod.objects.filter(owner=fan, is_primary=True)
        assert primaries.count() == 1
        assert str(primaries.get().id) == target["id"]


def test_set_primary_scoped_to_owner_is_404(client: Client) -> None:
    """Promoting another fan's method is a 404 (owner-scoped, no existence leak)."""
    fan = _fan()
    other = _fan()
    created = _post(
        client, BASE, {"brand": "VISA", "card_number": "4111111111111111"}, headers=_auth(fan)
    ).json()
    assert client.post(f"{BASE}/{created['id']}/primary", headers=_auth(other)).status_code == 404


def test_single_primary_partial_unique_rejects_second_primary(client: Client) -> None:
    """The per-owner partial-unique rejects a second primary row — the invariant guarded.

    Mirrors the subscription/refund constraint tests: a direct duplicate primary insert
    must raise ``IntegrityError``, which is the DB backstop behind the endpoint's
    atomic + row-lock swap (and its ``IntegrityError`` → re-read fallback).
    """
    fan = _fan()
    SavedPaymentMethod.objects.create(owner=fan, brand="VISA", last4="1111", is_primary=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        SavedPaymentMethod.objects.create(
            owner=fan, brand="MASTER", last4="0004", is_primary=True
        )
