"""Structured API error codes + a coded ``HttpError`` (R4-W1 hardening, ASS-257).

The web branches on the *reason* an API call failed, not on the human-facing
``detail`` string (which is copy that changes). Before this module the only
machine-readable signal was the HTTP status, so the web had to string-match
``detail`` (e.g. login 422 "가입이 필요해요" vs "인증번호가 올바르지 않아요") — brittle
and locale-bound.

This module adds a stable, machine-readable ``code`` alongside the existing
``detail`` (backward-compatible — ``detail`` is unchanged, ``code`` is additive):

- Endpoints that signal errors by **raising** ``HttpError`` (identity, payments,
  dashboard) raise :class:`ApiError` instead, which carries a :class:`ErrorCode`
  and renders ``{"detail": ..., "code": ...}`` via the handler registered by
  :func:`register_error_handlers`.
- Endpoints that signal errors by **returning** an error schema (commerce,
  membership, payments) add a ``code: str`` field to that schema and populate it
  from :class:`ErrorCode`.

Contract stability: an :class:`ErrorCode` *value* is the wire contract the web
keys on — never rename an existing value; only add new members.
"""

from __future__ import annotations

from enum import StrEnum

from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import HttpError


class ErrorCode(StrEnum):
    """Stable, machine-readable API error codes (the web branches on these).

    Values are deliberately PascalCase identifiers decoupled from HTTP status and
    from the human ``detail`` copy, so the web can switch on a reason without
    string-matching a localized message. Grouped by domain; add new members, never
    rename existing values.
    """

    # --- generic / infrastructure -------------------------------------------
    SERVICE_UNAVAILABLE = "ServiceUnavailable"

    # --- identity / auth ----------------------------------------------------
    ACCOUNT_NOT_REGISTERED = "AccountNotRegistered"
    OTP_INVALID = "OtpInvalid"
    OTP_UNAVAILABLE = "OtpUnavailable"
    PHONE_INVALID = "PhoneInvalid"
    CONSENT_REQUIRED = "ConsentRequired"
    CSRF_FAILED = "CsrfFailed"
    REFRESH_TOKEN_REQUIRED = "RefreshTokenRequired"
    REFRESH_TOKEN_INVALID = "RefreshTokenInvalid"
    KYC_UNAVAILABLE = "KycUnavailable"

    # --- commerce (catalog / studio) ----------------------------------------
    OWNER_REQUIRED = "OwnerRequired"
    PRODUCT_NOT_FOUND = "ProductNotFound"
    PRODUCT_TYPE_INVALID = "ProductTypeInvalid"
    PRODUCT_STATUS_INVALID = "ProductStatusInvalid"

    # --- commerce (orders) --------------------------------------------------
    PRODUCT_NOT_ORDERABLE = "ProductNotOrderable"
    MEMBERSHIP_ONLY_PRODUCT = "MembershipOnlyProduct"
    OUT_OF_STOCK = "OutOfStock"
    INSUFFICIENT_STOCK = "InsufficientStock"
    ORDER_NOT_FOUND = "OrderNotFound"
    ORDER_NOT_CANCELLABLE = "OrderNotCancellable"
    ORDER_NOT_REFUNDABLE = "OrderNotRefundable"
    OPEN_REFUND_EXISTS = "OpenRefundExists"

    # --- membership ---------------------------------------------------------
    TIER_NOT_FOUND = "TierNotFound"
    TIER_IN_USE = "TierInUse"
    DUPLICATE_SUBSCRIPTION = "DuplicateSubscription"
    SUBSCRIPTION_NOT_FOUND = "SubscriptionNotFound"
    SUBSCRIPTION_NOT_CANCELLABLE = "SubscriptionNotCancellable"

    # --- payments -----------------------------------------------------------
    PAYMENTS_UNAVAILABLE = "PaymentsUnavailable"
    PAYMENT_CARD_INVALID = "PaymentCardInvalid"
    PAYMENT_METHOD_NOT_FOUND = "PaymentMethodNotFound"

    # --- dashboard ----------------------------------------------------------
    DATE_RANGE_INVALID = "DateRangeInvalid"

    # --- gating (adult 19+) -------------------------------------------------
    # Reserved: the 19+ gate currently *hides* gated items (404 / filtered out) so
    # existence never leaks, rather than raising an explicit block. This code exists
    # for a future surface that returns an explicit "blocked by age gate" error.
    ADULT_GATE_BLOCKED = "AdultGateBlocked"


class ApiError(HttpError):
    """An ``HttpError`` that also carries a stable :class:`ErrorCode`.

    Subclasses ninja's ``HttpError`` so existing ``except HttpError`` paths and the
    default status handling keep working; the handler registered by
    :func:`register_error_handlers` renders it as ``{"detail": ..., "code": ...}``.
    Because :func:`NinjaAPI._lookup_exception_handler` resolves by the exception's
    MRO, the ``ApiError`` handler is matched before the base ``HttpError`` one.
    """

    def __init__(self, status_code: int, message: str, *, code: ErrorCode) -> None:
        """Bind an HTTP status, a human ``detail`` message, and a stable ``code``."""
        self.code = code
        super().__init__(status_code, message)


def register_error_handlers(api: NinjaAPI) -> None:
    """Register the :class:`ApiError` handler on ``api`` (call once at api setup).

    Renders ``{"detail": <message>, "code": <ErrorCode value>}`` at the error's
    status. The default ninja ``HttpError`` handler (plain ``{"detail": ...}``) is
    left in place for any raise site that has not adopted a code yet, so the change
    is additive and backward-compatible.
    """

    @api.exception_handler(ApiError)
    def _handle_api_error(request: HttpRequest, exc: ApiError) -> HttpResponse:
        return api.create_response(
            request,
            {"detail": exc.message, "code": str(exc.code)},
            status=exc.status_code,
        )
