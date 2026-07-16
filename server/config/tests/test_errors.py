"""Tests for the structured error contract — {detail, code} (ASS-257 item 1).

Two layers: (1) the :class:`~config.errors.ApiError` handler renders ``code``
alongside the (unchanged) ``detail`` while a plain ``HttpError`` still renders
``detail`` only (backward compatible); (2) a returned error schema (commerce) also
carries ``code`` on the wire, not just the raised ``ApiError`` path.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client, RequestFactory
from ninja import NinjaAPI
from ninja.errors import HttpError, Throttled

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from config.errors import ApiError, ErrorCode, register_error_handlers

# --- handler rendering (unit) ------------------------------------------------


def test_api_error_carries_status_message_and_code() -> None:
    exc = ApiError(422, "인증번호가 올바르지 않아요.", code=ErrorCode.OTP_INVALID)
    assert exc.status_code == 422
    assert exc.message == "인증번호가 올바르지 않아요."
    assert str(exc) == "인증번호가 올바르지 않아요."
    assert exc.code is ErrorCode.OTP_INVALID
    assert isinstance(exc, HttpError)  # subclass → existing except-HttpError paths work


def test_handler_renders_detail_and_code() -> None:
    api = NinjaAPI()
    register_error_handlers(api)
    request = RequestFactory().post("/x")
    response = api.on_exception(
        request, ApiError(422, "가입이 필요해요.", code=ErrorCode.ACCOUNT_NOT_REGISTERED)
    )
    assert response.status_code == 422
    assert json.loads(response.content) == {
        "detail": "가입이 필요해요.",
        "code": "AccountNotRegistered",
    }


def test_plain_httperror_still_renders_detail_only() -> None:
    # Backward compatibility: a raise site that has not adopted a code renders exactly
    # as before — {detail} with no code key.
    api = NinjaAPI()
    register_error_handlers(api)
    request = RequestFactory().post("/x")
    response = api.on_exception(request, HttpError(422, "plain"))
    assert json.loads(response.content) == {"detail": "plain"}


def test_throttled_handler_adds_code_and_retry_after() -> None:
    # A ninja throttle rejection renders a coded 429 plus a Retry-After header
    # (seconds, rounded up from the recommended wait).
    api = NinjaAPI()
    register_error_handlers(api)
    response = api.on_exception(RequestFactory().post("/x"), Throttled(wait=13))
    assert response.status_code == 429
    assert json.loads(response.content) == {
        "detail": "Too many requests.",
        "code": "RateLimited",
    }
    assert response["Retry-After"] == "13"


def test_throttled_handler_without_wait_omits_retry_after() -> None:
    api = NinjaAPI()
    register_error_handlers(api)
    response = api.on_exception(RequestFactory().post("/x"), Throttled(wait=None))
    assert response.status_code == 429
    assert response.has_header("Retry-After") is False


def test_error_code_values_are_stable() -> None:
    # These string values are the wire contract the web branches on — pin a sample so
    # a rename is caught here.
    assert ErrorCode.ACCOUNT_NOT_REGISTERED.value == "AccountNotRegistered"
    assert ErrorCode.OTP_INVALID.value == "OtpInvalid"
    assert ErrorCode.OWNER_REQUIRED.value == "OwnerRequired"
    assert ErrorCode.DUPLICATE_SUBSCRIPTION.value == "DuplicateSubscription"
    assert ErrorCode.OPEN_REFUND_EXISTS.value == "OpenRefundExists"
    assert str(ErrorCode.PRODUCT_NOT_ORDERABLE) == "ProductNotOrderable"
    assert ErrorCode.SHIPPING_ADDRESS_REQUIRED.value == "ShippingAddressRequired"
    assert ErrorCode.SUBSCRIPTION_NOT_ACTIVE.value == "SubscriptionNotActive"
    assert ErrorCode.RATE_LIMITED.value == "RateLimited"


# --- returned error schema also carries code (integration) -------------------


@pytest.mark.django_db
def test_returned_commerce_error_carries_code(client: Client) -> None:
    # The order endpoints signal errors by *returning* CommerceError; prove the added
    # `code` field reaches the wire (not just the raised ApiError path).
    account = Account.objects.create(role=Role.FAN.value, nickname="미오팬")
    token = issue_token_pair(account).access_token
    resp = client.get(
        "/api/orders/UNKNOWN-ORDER-ID",
        headers={"authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"] == "주문을 찾을 수 없어요."
    assert body["code"] == "OrderNotFound"
