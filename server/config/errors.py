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

import math
from enum import StrEnum

from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import HttpError, Throttled


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
    # A product with order history can't be hard-deleted (would SET_NULL the
    # historical OrderItem.product FK, breaking stats attribution) — the owner
    # must archive it (status=hidden) instead. Mirrors TIER_IN_USE below.
    PRODUCT_HAS_ORDERS = "ProductHasOrders"

    # --- commerce (orders) --------------------------------------------------
    PRODUCT_NOT_ORDERABLE = "ProductNotOrderable"
    MEMBERSHIP_ONLY_PRODUCT = "MembershipOnlyProduct"
    OUT_OF_STOCK = "OutOfStock"
    INSUFFICIENT_STOCK = "InsufficientStock"
    # A physical (goods) order was placed without a delivery address.
    SHIPPING_ADDRESS_REQUIRED = "ShippingAddressRequired"
    ORDER_NOT_FOUND = "OrderNotFound"
    ORDER_NOT_CANCELLABLE = "OrderNotCancellable"
    ORDER_NOT_REFUNDABLE = "OrderNotRefundable"
    OPEN_REFUND_EXISTS = "OpenRefundExists"
    # --- commerce (operator refund review, R6-W1A) --------------------------
    # A refund request id was not found in the operator queue.
    REFUND_NOT_FOUND = "RefundNotFound"
    # A refund state transition (review/accept/reject) was attempted from a state
    # that does not permit it — e.g. accepting an already-resolved request. Emitted
    # by the conditional-UPDATE rowcount gate (0 rows won → 422), the same seal the
    # order cancel path uses, so a double accept/reject can never re-run its effects.
    REFUND_NOT_TRANSITIONABLE = "RefundNotTransitionable"

    # --- membership ---------------------------------------------------------
    TIER_NOT_FOUND = "TierNotFound"
    TIER_IN_USE = "TierInUse"
    DUPLICATE_SUBSCRIPTION = "DuplicateSubscription"
    SUBSCRIPTION_NOT_FOUND = "SubscriptionNotFound"
    SUBSCRIPTION_NOT_CANCELLABLE = "SubscriptionNotCancellable"
    # A tier change (up/downgrade) was attempted on a non-active subscription.
    SUBSCRIPTION_NOT_ACTIVE = "SubscriptionNotActive"

    # --- rate limiting ------------------------------------------------------
    # Emitted with a 429 (+ Retry-After) when the per-client rate is exceeded.
    RATE_LIMITED = "RateLimited"

    # --- payments -----------------------------------------------------------
    PAYMENTS_UNAVAILABLE = "PaymentsUnavailable"
    PAYMENT_CARD_INVALID = "PaymentCardInvalid"
    PAYMENT_METHOD_NOT_FOUND = "PaymentMethodNotFound"

    # --- dashboard ----------------------------------------------------------
    DATE_RANGE_INVALID = "DateRangeInvalid"

    # --- social (personal block) --------------------------------------------
    # A fan's *personal* block of a creator (apps.social.CreatorBlock) — distinct
    # from operator moderation (apps.safety.UserBlock). Raised only when the block
    # target creator does not exist; blocking is otherwise idempotent.
    BLOCK_TARGET_NOT_FOUND = "BlockTargetNotFound"
    # A write interaction (like/comment/order) against content owned by a creator
    # the actor has personally blocked is refused (422). Direct *reads* stay allowed
    # (a personal block is not existence hiding) — only new interactions are denied.
    INTERACTION_BLOCKED = "InteractionBlocked"

    # --- gating (adult 19+) -------------------------------------------------
    # Reserved: the 19+ gate currently *hides* gated items (404 / filtered out) so
    # existence never leaks, rather than raising an explicit block. This code exists
    # for a future surface that returns an explicit "blocked by age gate" error.
    ADULT_GATE_BLOCKED = "AdultGateBlocked"

    # --- uploads (media) ----------------------------------------------------
    # A multipart image upload was rejected (apps.uploads.api): the declared
    # content-type is not an allowed image family (415 → UPLOAD_TYPE_UNSUPPORTED,
    # also covers SVG/HTML); the bytes are not a real image or are scriptable
    # markup — magic-byte sniff (422 → UPLOAD_INVALID); or the file exceeds the size
    # ceiling (413 → UPLOAD_TOO_LARGE).
    UPLOAD_TYPE_UNSUPPORTED = "UploadTypeUnsupported"
    UPLOAD_INVALID = "UploadInvalid"
    UPLOAD_TOO_LARGE = "UploadTooLarge"
    # The upload surface is fail-closed off (503): no real object-storage backend is
    # wired yet, so the endpoint only accepts writes in an environment that also
    # serves the stored bytes locally (settings.SERVE_LOCAL_MEDIA). With that off
    # (prod) an accepted upload would write to a local disk nothing can serve — so it
    # refuses instead, guarding against un-renderable objects and disk exhaustion.
    UPLOAD_STORAGE_UNAVAILABLE = "UploadStorageUnavailable"


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

    @api.exception_handler(Throttled)
    def _handle_throttled(request: HttpRequest, exc: Throttled) -> HttpResponse:
        """Render a ninja throttle rejection as a coded 429 with ``Retry-After``.

        Ninja's default handler emits a bare ``{"detail": ...}`` 429; this adds the
        stable ``code`` the web branches on and a ``Retry-After`` header (seconds,
        rounded up from the throttle's recommended wait) so a client backs off
        deterministically. Registered here because ``Throttled`` subclasses
        ``HttpError`` and MRO resolution matches this handler first.
        """
        response = api.create_response(
            request,
            {"detail": "Too many requests.", "code": ErrorCode.RATE_LIMITED.value},
            status=429,
        )
        if exc.wait is not None:
            response["Retry-After"] = str(max(1, math.ceil(exc.wait)))
        return response
