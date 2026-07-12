"""Tests for the hosted-commerce bridge (integration seam, fail-closed).

Covers the webhook receiver's fail-closed gating + HMAC verification, idempotency, the
external-order → settlement-ledger attribution, the auth bridge, and the catalog export
shape. The bridge is OFF by default, so the enabled tests opt in via override_settings.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import pytest
from django.test import Client, override_settings

from apps.commerce.models import Product
from apps.commerce_bridge.models import ExternalCommerceOrder
from apps.commerce_bridge.product_sync import product_export
from apps.commerce_bridge.services import resolve_buyer
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.payments.models import PaymentAttempt, PaymentProvider

pytestmark = pytest.mark.django_db

_SECRET = "test-webhook-secret"
_URL = "/api/integrations/commerce/generic/webhook"


def _sign(body: bytes, secret: str = _SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _event(**overrides: Any) -> bytes:
    payload = {
        "event_id": "evt-1",
        "event_type": "order_paid",
        "external_order_id": "ord-1",
        "creator_ref": "",
        "buyer_ref": "",
        "amount": 15000,
        "currency": "KRW",
    }
    payload.update(overrides)
    return json.dumps(payload).encode("utf-8")


def _post(client: Client, body: bytes, sig: str | None = None) -> Any:
    return client.post(
        _URL,
        data=body,
        content_type="application/json",
        headers={"x-assen-signature": sig if sig is not None else _sign(body)},
    )


def test_webhook_fails_closed_when_bridge_disabled(client: Client) -> None:
    # ENABLE_COMMERCE_BRIDGE defaults False → 503, nothing recorded.
    resp = _post(client, _event())
    assert resp.status_code == 503
    assert not ExternalCommerceOrder.objects.exists()


@override_settings(ENABLE_COMMERCE_BRIDGE=True, COMMERCE_BRIDGE_WEBHOOK_SECRET=_SECRET)
def test_webhook_rejects_bad_signature(client: Client) -> None:
    resp = _post(client, _event(), sig="deadbeef")
    assert resp.status_code == 401
    assert not ExternalCommerceOrder.objects.exists()


@override_settings(ENABLE_COMMERCE_BRIDGE=True, COMMERCE_BRIDGE_WEBHOOK_SECRET="")
def test_webhook_fails_closed_without_secret(client: Client) -> None:
    # Even a signature that would verify against an empty key is refused.
    body = _event()
    resp = _post(client, body, sig=_sign(body, secret=""))
    assert resp.status_code == 401


@override_settings(ENABLE_COMMERCE_BRIDGE=True, COMMERCE_BRIDGE_WEBHOOK_SECRET=_SECRET)
def test_paid_webhook_records_order_and_credits_settlement(client: Client) -> None:
    creator = Creator.objects.create(handle="stellar", name="별빛")
    resp = _post(client, _event(creator_ref="stellar", amount=20000))

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "duplicate": False}
    order = ExternalCommerceOrder.objects.get(external_order_id="ord-1")
    assert order.creator_id == creator.id
    assert order.amount == 20000
    assert order.status == "paid"
    # The shared settlement ledger is credited with an EXTERNAL attempt.
    attempt = PaymentAttempt.objects.get(external_order=order)
    assert attempt.provider == PaymentProvider.EXTERNAL.value
    assert attempt.authorized_amount == 20000
    assert attempt.provider_txn_id == "generic:ord-1"


@override_settings(ENABLE_COMMERCE_BRIDGE=True, COMMERCE_BRIDGE_WEBHOOK_SECRET=_SECRET)
def test_duplicate_event_is_idempotent(client: Client) -> None:
    body = _event()
    assert _post(client, body).status_code == 200
    second = _post(client, body)

    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert ExternalCommerceOrder.objects.filter(external_order_id="ord-1").count() == 1
    # Retried delivery must NOT double-credit the ledger.
    assert PaymentAttempt.objects.count() == 1


@override_settings(ENABLE_COMMERCE_BRIDGE=True, COMMERCE_BRIDGE_WEBHOOK_SECRET=_SECRET)
def test_unknown_event_type_is_refused(client: Client) -> None:
    resp = _post(client, _event(event_type="order_frobnicated", event_id="evt-x"))
    assert resp.status_code == 400


def test_resolve_buyer_maps_fan_id_or_none() -> None:
    account = Account.objects.create(role=Role.FAN.value)
    assert resolve_buyer(str(account.fan_id)) == account
    assert resolve_buyer("") is None
    assert resolve_buyer("not-a-uuid") is None


def test_product_export_shape_includes_creator_tag() -> None:
    creator = Creator.objects.create(handle="stellar", name="별빛")
    product = Product.objects.create(
        creator=creator, type="goods", title="체키", price=5000
    )
    out = product_export(product)
    assert out["title"] == "체키"
    assert out["price"] == 5000
    assert out["type"] == "goods"
    assert out["creator_ref"] == "stellar"
