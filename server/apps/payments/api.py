"""Saved payment methods API (R3 — mock tokenization, no PAN stored).

Fan surface (``fan_auth``): register a (mock) payment method, list one's own, set a
primary, and delete. 법무/보안 경계: the card PAN never persists — the mock tokenizer
keeps only brand + last4 + a placeholder token, and no expiry/cvc is accepted at all.
Real PG tokenization is a 대표·법무·PG gate (see :mod:`config.payment`).

Endpoints (``/api/fan/payment-methods``):
- ``GET  ``            — the fan's own saved methods.
- ``POST ``            — register a (mock) method; fails closed (503) if unwired.
- ``POST /{id}/primary`` — make one of the fan's methods primary.
- ``DELETE /{id}``     — remove one of the fan's methods.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import cast

from django.db import IntegrityError, transaction
from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from apps.identity.auth import fan_auth
from apps.identity.models import Account
from apps.payments.models import SavedPaymentMethod
from config.api import api
from config.payment import PaymentError, payment_tokenizer
from config.throttle import user_write_throttle

payment_methods_router = Router(auth=fan_auth, tags=["payment-methods"])


class PaymentMethodError(Schema):
    """Stable error shape for payment-method endpoints."""

    detail: str


class PaymentAck(Schema):
    """Bare status ack for a mutation that returns no body (delete)."""

    status: str


class PaymentMethodOut(Schema):
    """A saved payment method — display metadata only (never a PAN)."""

    id: uuid.UUID
    brand: str
    last4: str
    is_primary: bool
    created_at: datetime


class PaymentMethodIn(Schema):
    """Payload to register a (mock) payment method.

    ``card_number`` is a MOCK card used ONLY to derive the display last4; the
    tokenizer discards it and it is never stored or logged (R4 / PCI). No expiry/cvc
    is accepted at all — those are out of scope for the mock and forbidden to store.
    """

    brand: str = Field(default="", max_length=20)
    card_number: str = Field(min_length=4, max_length=32)
    make_primary: bool = False


def _method_out(method: SavedPaymentMethod) -> PaymentMethodOut:
    """Build the payment-method response (never exposes a PAN)."""
    return PaymentMethodOut(
        id=method.id,
        brand=method.brand,
        last4=method.last4,
        is_primary=method.is_primary,
        created_at=method.created_at,
    )


@payment_methods_router.get("", response=list[PaymentMethodOut])
def list_payment_methods(request: HttpRequest) -> list[PaymentMethodOut]:
    """List the requesting fan's own saved payment methods (newest first)."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    methods = SavedPaymentMethod.objects.filter(owner=account).order_by("-created_at")
    return [_method_out(m) for m in methods]


@payment_methods_router.post(
    "",
    response={201: PaymentMethodOut, 422: PaymentMethodError},
    throttle=user_write_throttle("10/min"),
)
def register_payment_method(
    request: HttpRequest, payload: PaymentMethodIn
) -> tuple[int, PaymentMethodOut | PaymentMethodError]:
    """Register a (mock) payment method for the requesting fan.

    Fail-closed (503) when no tokenizer is wired. The mock tokenizer discards the
    card, keeping only brand + last4 + a placeholder token — the PAN never touches
    the DB or logs. The first method (or one flagged ``make_primary``) becomes
    primary; the per-owner partial-unique constraint keeps at most one primary.
    """
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    tokenizer = payment_tokenizer()
    if tokenizer is None:
        raise HttpError(503, "결제수단 등록을 사용할 수 없어요.")
    try:
        card = tokenizer.tokenize(card_number=payload.card_number, brand=payload.brand)
    except PaymentError:
        return 422, PaymentMethodError(detail="카드 정보가 올바르지 않아요.")
    # First method is primary by default; else honour make_primary. Decided before
    # insert; the DB constraint is the race-safe backstop in the except below.
    has_existing = SavedPaymentMethod.objects.filter(owner=account).exists()
    make_primary = payload.make_primary or not has_existing
    try:
        with transaction.atomic():
            if make_primary:
                SavedPaymentMethod.objects.filter(
                    owner=account, is_primary=True
                ).update(is_primary=False)
            method = SavedPaymentMethod.objects.create(
                owner=account,
                brand=card.brand,
                last4=card.last4,
                pg_token=card.pg_token,
                is_primary=make_primary,
            )
    except IntegrityError:
        # Two concurrent primary registrations raced; save this one as non-primary so
        # the method still persists (the earlier writer keeps primary).
        method = SavedPaymentMethod.objects.create(
            owner=account,
            brand=card.brand,
            last4=card.last4,
            pg_token=card.pg_token,
            is_primary=False,
        )
    return 201, _method_out(method)


@payment_methods_router.post(
    "/{method_id}/primary",
    response={200: PaymentMethodOut, 404: PaymentMethodError},
    throttle=user_write_throttle("10/min"),
)
def set_primary_payment_method(
    request: HttpRequest, method_id: uuid.UUID
) -> tuple[int, PaymentMethodOut | PaymentMethodError]:
    """Make one of the fan's own methods primary (404 if not theirs).

    Demotes the current primary and promotes the target in one transaction so the
    per-owner single-primary constraint is never transiently violated. The owner's
    method rows are locked (``select_for_update``) for the swap so two concurrent
    promotions (or one racing a ``make_primary`` registration) serialise instead of
    both inserting/updating a primary and tripping the partial-unique constraint; an
    ``IntegrityError`` from a lost race is caught and the current state re-read rather
    than surfaced as a 500.
    """
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    method = SavedPaymentMethod.objects.filter(id=method_id, owner=account).first()
    if method is None:
        return 404, PaymentMethodError(detail="결제수단을 찾을 수 없어요.")
    if not method.is_primary:
        try:
            with transaction.atomic():
                # Lock all of this owner's methods so concurrent primary switches
                # serialise (no-op on sqlite; a real lock on Postgres).
                list(SavedPaymentMethod.objects.select_for_update().filter(owner=account))
                SavedPaymentMethod.objects.filter(
                    owner=account, is_primary=True
                ).update(is_primary=False)
                method.is_primary = True
                method.save(update_fields=["is_primary"])
        except IntegrityError:
            # A concurrent promotion won the primary slot; return the freshest state
            # instead of surfacing the constraint error as a 500.
            refreshed = SavedPaymentMethod.objects.filter(
                id=method_id, owner=account
            ).first()
            if refreshed is not None:
                method = refreshed
    return 200, _method_out(method)


@payment_methods_router.delete(
    "/{method_id}",
    response={200: PaymentAck, 404: PaymentMethodError},
    throttle=user_write_throttle("10/min"),
)
def delete_payment_method(
    request: HttpRequest, method_id: uuid.UUID
) -> tuple[int, PaymentAck | PaymentMethodError]:
    """Delete one of the fan's own saved methods (404 if not theirs)."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    method = SavedPaymentMethod.objects.filter(id=method_id, owner=account).first()
    if method is None:
        return 404, PaymentMethodError(detail="결제수단을 찾을 수 없어요.")
    method.delete()
    return 200, PaymentAck(status="deleted")


api.add_router("/fan/payment-methods", payment_methods_router)
