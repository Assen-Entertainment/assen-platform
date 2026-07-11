"""ASS-298 — payment provenance + ledger (commerce).

A successful mock order records ``payment_provenance=mock`` and writes exactly one
succeeded MOCK :class:`PaymentAttempt` linked to the order (and to no
subscription). A raw ``Order`` created without a provenance backfills to
``legacy_unknown`` — the same default the migration applies to pre-existing rows,
so provenance is never guessed.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client, override_settings

from apps.commerce.models import Order, Product
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.payments.models import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentProvider,
)
from config.payment import PaymentProvenance

pytestmark = pytest.mark.django_db

BASE = "/api/orders"
JSON = "application/json"


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    """Return test-client headers bearing an issued access token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _product(**kwargs: object) -> Product:
    """Create an orderable digital product (no shipping gate involved)."""
    defaults: dict[str, object] = {"type": "digital", "title": "디지털", "price": 5000}
    defaults.update(kwargs)
    creator = Creator.objects.create(handle="stellar", name="별빛")
    defaults.setdefault("creator", creator)
    return Product.objects.create(**defaults)


@override_settings(ENABLE_MOCK_PAYMENT=True)
def test_paid_order_records_mock_provenance_and_one_ledger_row(client: Client) -> None:
    """A mock order is tagged ``mock`` and ledgers exactly one succeeded attempt."""
    fan = _fan()
    product = _product(price=7000)
    res = client.post(
        BASE,
        data=json.dumps({"product_id": str(product.id), "qty": 2}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    order = Order.objects.get()
    assert order.payment_provenance == PaymentProvenance.MOCK
    assert order.total == 14000

    attempts = list(PaymentAttempt.objects.filter(order=order))
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt.provider == PaymentProvider.MOCK
    assert attempt.status == PaymentAttemptStatus.SUCCEEDED
    assert attempt.authorized_amount == order.total
    assert attempt.currency == "KRW"
    assert attempt.subscription_id is None
    assert attempt.provider_txn_id == f"mock_{order.id}"


def test_raw_order_defaults_to_legacy_unknown() -> None:
    """A row created without a provenance is ``legacy_unknown`` — never guessed."""
    order = Order.objects.create(buyer=_fan())
    assert order.payment_provenance == PaymentProvenance.LEGACY_UNKNOWN
