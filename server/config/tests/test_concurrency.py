"""Real-race concurrency tests for the ``select_for_update`` / rowcount-gate paths.

These prove that the serialization invariants documented across the money paths hold
under *actual* thread contention on real PostgreSQL — not just single-threaded logic:

- coupon double-redeem (``redeem_coupon`` — ``select_for_update`` lock),
- order stock deduction (``create_order`` — ``stock__gte`` conditional-UPDATE gate),
- payment-method primary switch (``set_primary`` — ``select_for_update`` + the
  per-owner single-primary partial-unique constraint).

They use :class:`~django.test.TransactionTestCase` (each request/thread commits and
sees the others' committed rows) plus a :class:`threading.Barrier` so the workers
collide inside the critical section. ``select_for_update`` is a **no-op on sqlite**
(and threaded writes there just lock the file), so the whole case self-skips unless
the suite runs on PostgreSQL — i.e. it is exercised by
``DJANGO_SETTINGS_MODULE=config.settings.test_pg`` and skipped by the default sqlite
``pytest -q`` run.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from typing import Any

from django.db import connection
from django.test import Client, TransactionTestCase

from apps.commerce.models import Order, Product, ProductType
from apps.coupon.models import Coupon, CouponStatus, CouponType
from apps.coupon.services import issue_coupon, redeem_coupon
from apps.creator.models import Creator
from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.payments.models import SavedPaymentMethod

JSON = "application/json"


def _run_concurrently(
    funcs: list[Callable[[], Any]],
) -> tuple[list[Any], list[BaseException | None]]:
    """Run ``funcs`` in parallel threads that all release from one barrier.

    Each worker closes its own DB connection on exit (threads get their own
    connection, which the test-case teardown would otherwise not reap). Returns the
    per-worker results and any raised exceptions, positionally aligned with ``funcs``.
    """
    barrier = threading.Barrier(len(funcs))
    results: list[Any] = [None] * len(funcs)
    errors: list[BaseException | None] = [None] * len(funcs)

    def worker(index: int, func: Callable[[], Any]) -> None:
        try:
            barrier.wait()
            results[index] = func()
        except BaseException as exc:  # noqa: BLE001 - recorded for the assertion
            errors[index] = exc
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i, f)) for i, f in enumerate(funcs)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results, errors


class ConcurrencySelectForUpdateTests(TransactionTestCase):
    """Thread-level races over the locked money paths (PostgreSQL only)."""

    def setUp(self) -> None:
        """Skip entirely unless the backend is PostgreSQL (see module docstring)."""
        if connection.vendor != "postgresql":
            self.skipTest(
                "select_for_update is a no-op on sqlite; run with config.settings.test_pg"
            )

    def _auth(self, account: Account) -> dict[str, str]:
        """Bearer header for ``account`` (mirrors the commerce test helper)."""
        return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}

    def test_double_redeem_serializes_to_one_winner(self) -> None:
        """Two concurrent redeems of one coupon: exactly one wins, one is refused."""
        operator = Account.objects.create(role=Role.OPERATOR.value)
        fan = Account.objects.create(role=Role.FAN.value)
        coupon = issue_coupon(fan=fan, coupon_type=CouponType.REVISIT.value, actor=operator)

        def redeem() -> Coupon:
            return redeem_coupon(coupon=coupon, actor=operator)

        results, errors = _run_concurrently([redeem, redeem])

        successes = [r for r in results if r is not None]
        failures = [e for e in errors if e is not None]
        self.assertEqual(len(successes), 1, "exactly one redeem should commit")
        self.assertEqual(len(failures), 1, "the loser should be refused, not crash")
        self.assertIsInstance(failures[0], ValueError)
        coupon.refresh_from_db()
        self.assertEqual(coupon.status, CouponStatus.REDEEMED.value)
        self.assertIsNotNone(coupon.redemption_id)
        # The winner emits exactly one redeemed signal (the loser emits none).
        self.assertEqual(
            EventRecord.objects.filter(event_name=EventName.COUPON_REDEEMED.value).count(), 1
        )

    def test_last_unit_cannot_be_oversold(self) -> None:
        """Two buyers racing for the last unit: one 201, one 422, stock never < 0."""
        creator = Creator.objects.create(handle="stellar", name="별빛")
        product = Product.objects.create(
            type=ProductType.DIGITAL.value, title="음원", price=1000, stock=1, creator=creator
        )
        buyer_a = Account.objects.create(role=Role.FAN.value)
        buyer_b = Account.objects.create(role=Role.FAN.value)
        body = json.dumps({"product_id": str(product.id), "qty": 1})

        def order(account: Account) -> int:
            response = Client().post(
                "/api/orders", data=body, content_type=JSON, headers=self._auth(account)
            )
            return int(response.status_code)

        results, _ = _run_concurrently([lambda: order(buyer_a), lambda: order(buyer_b)])

        self.assertEqual(sorted(results), [201, 422], "exactly one order should be accepted")
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)
        self.assertEqual(Order.objects.count(), 1)

    def test_primary_switch_keeps_a_single_primary(self) -> None:
        """Two concurrent primary promotions serialize to exactly one primary, no 500."""
        owner = Account.objects.create(role=Role.FAN.value)
        SavedPaymentMethod.objects.create(owner=owner, brand="VISA", last4="0001", is_primary=True)
        second = SavedPaymentMethod.objects.create(owner=owner, brand="VISA", last4="0002")
        third = SavedPaymentMethod.objects.create(owner=owner, brand="VISA", last4="0003")
        headers = self._auth(owner)

        def promote(method_id: str) -> int:
            response = Client().post(
                f"/api/fan/payment-methods/{method_id}/primary",
                content_type=JSON,
                headers=headers,
            )
            return int(response.status_code)

        results, errors = _run_concurrently(
            [lambda: promote(str(second.id)), lambda: promote(str(third.id))]
        )

        self.assertEqual(results, [200, 200], "neither promotion should 500")
        self.assertTrue(all(e is None for e in errors))
        self.assertEqual(
            SavedPaymentMethod.objects.filter(owner=owner, is_primary=True).count(),
            1,
            "the single-primary constraint must hold under contention",
        )
