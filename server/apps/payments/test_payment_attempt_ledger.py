"""ASS-298 — PaymentAttempt ledger model invariants.

The XOR ``CheckConstraint`` guarantees an attempt settles exactly one target — an
order or a subscription, never both and never neither — so a ledger row can never
be orphaned or double-linked.
"""

from __future__ import annotations

import datetime

import pytest
from django.db import IntegrityError, transaction

from apps.commerce.models import Order
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.membership.models import MembershipTier, Subscription
from apps.payments.models import PaymentAttempt, PaymentProvider

pytestmark = pytest.mark.django_db


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def test_attempt_requires_a_target() -> None:
    """An attempt linked to neither an order nor a subscription is rejected."""
    with pytest.raises(IntegrityError), transaction.atomic():
        PaymentAttempt.objects.create(
            provider=PaymentProvider.MOCK, authorized_amount=0
        )


def test_attempt_rejects_both_targets() -> None:
    """An attempt linked to BOTH an order and a subscription is rejected."""
    fan = _fan()
    creator = Creator.objects.create(handle="stellar", name="별빛")
    order = Order.objects.create(buyer=fan)
    tier = MembershipTier.objects.create(creator=creator, name="스탠다드", price=9900)
    sub = Subscription.objects.create(
        fan=fan, tier=tier, next_billing_date=datetime.date(2026, 1, 1)
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        PaymentAttempt.objects.create(
            order=order,
            subscription=sub,
            provider=PaymentProvider.MOCK,
            authorized_amount=0,
        )
