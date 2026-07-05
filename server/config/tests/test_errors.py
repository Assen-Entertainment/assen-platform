"""Tests for the structured error contract — {detail, code} (ASS-257 item 1).

Two layers: (1) the :class:`~config.errors.ApiError` handler renders ``code``
alongside the (unchanged) ``detail`` while a plain ``HttpError`` still renders
``detail`` only (backward compatible); (2) the critical web branches carry the
right code on the wire — login "가입 필요" vs "OTP 오류", and a returned error
schema (commerce) also carries ``code``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client, RequestFactory, override_settings
from ninja import NinjaAPI
from ninja.errors import HttpError

from apps.identity.signup_services import register_fan
from config.errors import ApiError, ErrorCode, register_error_handlers
from config.otp import MockOtpSender

_SENDER = MockOtpSender()
_PHONE = "+821012345678"


def _code() -> str:
    return _SENDER.code_for(_PHONE)


def _wrong_code() -> str:
    good = _code()
    return "654321" if good != "654321" else "123456"


def _post(client: Client, path: str, body: dict[str, object]) -> Any:
    return client.post(path, data=json.dumps(body), content_type="application/json")


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


def test_error_code_values_are_stable() -> None:
    # These string values are the wire contract the web branches on — pin a sample so
    # a rename is caught here.
    assert ErrorCode.ACCOUNT_NOT_REGISTERED.value == "AccountNotRegistered"
    assert ErrorCode.OTP_INVALID.value == "OtpInvalid"
    assert ErrorCode.OWNER_REQUIRED.value == "OwnerRequired"
    assert ErrorCode.DUPLICATE_SUBSCRIPTION.value == "DuplicateSubscription"
    assert ErrorCode.OPEN_REFUND_EXISTS.value == "OpenRefundExists"
    assert str(ErrorCode.PRODUCT_NOT_ORDERABLE) == "ProductNotOrderable"


# --- critical login branch (integration) -------------------------------------


@pytest.mark.django_db
def test_login_unregistered_carries_account_not_registered_code(client: Client) -> None:
    resp = _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _code()})
    assert resp.status_code == 422
    body = resp.json()
    # detail is unchanged (backward compatible); code is the new machine signal.
    assert body["detail"] == "가입이 필요해요."
    assert body["code"] == "AccountNotRegistered"


@pytest.mark.django_db
def test_login_bad_otp_carries_otp_invalid_code(client: Client) -> None:
    register_fan(
        phone=_PHONE,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_code(),
        otp_sender=_SENDER,
    )
    resp = _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": _wrong_code()})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "OtpInvalid"
    # The two 422s the web must tell apart now differ by code, not just by copy.
    assert body["detail"] != "가입이 필요해요."


@pytest.mark.django_db
@override_settings(ENABLE_MOCK_FAN_OTP=False)
def test_login_unavailable_carries_otp_unavailable_code(client: Client) -> None:
    resp = _post(client, "/api/fan/login", {"phone": _PHONE, "otp_code": "123456"})
    assert resp.status_code == 503
    assert resp.json()["code"] == "OtpUnavailable"


# --- returned error schema also carries code (integration) -------------------


@pytest.mark.django_db
def test_returned_commerce_error_carries_code(client: Client) -> None:
    # The order endpoints signal errors by *returning* CommerceError; prove the added
    # `code` field reaches the wire (not just the raised ApiError path).
    pair = register_fan(
        phone=_PHONE,
        nickname="미오팬",
        consent_terms=True,
        consent_privacy=True,
        otp_code=_code(),
        otp_sender=_SENDER,
    )
    resp = client.get(
        "/api/orders/UNKNOWN-ORDER-ID",
        headers={"authorization": f"Bearer {pair.access_token}"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"] == "주문을 찾을 수 없어요."
    assert body["code"] == "OrderNotFound"
