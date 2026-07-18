"""Tests for the flag-gated retention sweep (Codex #19).

The sweep is a fail-closed skeleton: with ``RETENTION_PURGE_ENABLED`` off it only
COUNTS rows past each window; with it on it runs the implemented per-class actions
(blank order shipping snapshots, delete expired token families) while still DEFERRING
the withdrawn-account final purge. Every run is idempotent.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.commerce.models import Order, OrderStatus
from apps.identity.models import Account, Role, TokenFamily
from apps.identity.retention import run_retention_sweep

pytestmark = pytest.mark.django_db


def _old(days: int) -> datetime:
    """A timestamp ``days`` in the past."""
    return timezone.now() - timedelta(days=days)


def _make_account() -> Account:
    """A bare fan account (no PII) to own the fixture rows."""
    return Account.objects.create(role=Role.FAN.value)


def _make_withdrawn_account(*, age_days: int) -> Account:
    """A withdrawn (anonymised) account whose ``withdrawn_at`` is ``age_days`` old."""
    account = _make_account()
    Account.objects.filter(pk=account.pk).update(withdrawn_at=_old(age_days))
    account.refresh_from_db()
    return account


def _make_expired_family(*, age_days: int) -> TokenFamily:
    """A revoked (dead) token family created ``age_days`` ago (auto_now_add bypass)."""
    account = _make_account()
    family = TokenFamily.objects.create(
        account=account, revoked=True, revoked_at=timezone.now()
    )
    TokenFamily.objects.filter(pk=family.pk).update(created_at=_old(age_days))
    family.refresh_from_db()
    return family


def _make_completed_order(*, age_days: int) -> Order:
    """A COMPLETED order carrying a delivery snapshot, completed ``age_days`` ago."""
    order: Order = Order.objects.create(
        buyer=_make_account(),
        status=OrderStatus.COMPLETED.value,
        recipient_name="미오",
        recipient_phone="010-0000-0002",
        postal_code="04524",
        address1="서울시 중구 세종대로 110",
        address2="8층",
        completed_at=_old(age_days),
    )
    return order


@override_settings(RETENTION_PURGE_ENABLED=False)
def test_flag_off_counts_but_changes_nothing() -> None:
    order = _make_completed_order(age_days=200)
    family = _make_expired_family(age_days=120)
    account = _make_withdrawn_account(age_days=60)

    result = run_retention_sweep()

    # Everything past its window is COUNTED...
    assert result["order_shipping_snapshots"] == 1
    assert result["expired_token_families"] == 1
    assert result["withdrawn_accounts"] == 1
    # ...but with the master switch off nothing is deleted or blanked (dry-run).
    order.refresh_from_db()
    assert order.recipient_name == "미오"
    assert order.recipient_phone == "010-0000-0002"
    assert TokenFamily.objects.filter(pk=family.pk).exists()
    assert Account.objects.filter(pk=account.pk).exists()


@override_settings(RETENTION_PURGE_ENABLED=True)
def test_flag_on_blanks_order_snapshot_and_deletes_token_family() -> None:
    order = _make_completed_order(age_days=200)
    family = _make_expired_family(age_days=120)

    run_retention_sweep()

    order.refresh_from_db()
    # The order ROW survives; only the recipient_* delivery PII is blanked.
    assert Order.objects.filter(pk=order.pk).exists()
    assert order.recipient_name == ""
    assert order.recipient_phone == ""
    assert order.postal_code == ""
    assert order.address1 == ""
    assert order.address2 == ""
    # A fully expired/revoked token family is safe hygiene — actually deleted.
    assert not TokenFamily.objects.filter(pk=family.pk).exists()


@override_settings(RETENTION_PURGE_ENABLED=True)
def test_flag_on_counts_withdrawn_account_but_defers_deletion() -> None:
    account = _make_withdrawn_account(age_days=60)

    result = run_retention_sweep()

    # Counted as past-window even with the flag on...
    assert result["withdrawn_accounts"] == 1
    # ...but the final purge is DEFERRED (법무 게이트) — the row is not deleted.
    assert Account.objects.filter(pk=account.pk).exists()


@override_settings(RETENTION_PURGE_ENABLED=True)
def test_sweep_is_idempotent() -> None:
    _make_completed_order(age_days=200)
    _make_expired_family(age_days=120)

    first = run_retention_sweep()
    assert first["order_shipping_snapshots"] == 1
    assert first["expired_token_families"] == 1

    # Second run: the implemented classes were already purged → nothing left to match.
    second = run_retention_sweep()
    assert second["order_shipping_snapshots"] == 0
    assert second["expired_token_families"] == 0


@override_settings(RETENTION_PURGE_ENABLED=True)
def test_rows_within_window_are_not_swept() -> None:
    order = _make_completed_order(age_days=10)
    family = _make_expired_family(age_days=10)

    result = run_retention_sweep()

    assert result["order_shipping_snapshots"] == 0
    assert result["expired_token_families"] == 0
    order.refresh_from_db()
    assert order.recipient_name == "미오"
    assert TokenFamily.objects.filter(pk=family.pk).exists()
