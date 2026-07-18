"""Tests for the data-retention sweep (D2/D6, privacy decisions 2026-07-12).

Only abandoned pre-signup AnonymousSession stubs (unmerged, >1 year) are purged;
merged and recent sessions are kept.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.identity.models import Account, AnonymousSession, Role
from apps.identity.retention import purge_anonymous_sessions, run_retention_sweep

pytestmark = pytest.mark.django_db


def _make_session(*, age_days: int, merged: Account | None = None) -> AnonymousSession:
    """Create an AnonymousSession, forcing created_at back (auto_now_add bypass)."""
    session = AnonymousSession.objects.create(merged_into=merged)
    old = timezone.now() - timedelta(days=age_days)
    AnonymousSession.objects.filter(pk=session.pk).update(created_at=old)
    session.refresh_from_db()
    return session


def test_purges_old_unmerged_session() -> None:
    _make_session(age_days=400)
    purged = purge_anonymous_sessions(now=timezone.now())
    assert purged == 1
    assert AnonymousSession.objects.count() == 0


def test_keeps_recent_unmerged_session() -> None:
    _make_session(age_days=10)
    purged = purge_anonymous_sessions(now=timezone.now())
    assert purged == 0
    assert AnonymousSession.objects.count() == 1


def test_keeps_old_but_merged_session() -> None:
    account = Account.objects.create(role=Role.FAN.value)
    _make_session(age_days=400, merged=account)
    purged = purge_anonymous_sessions(now=timezone.now())
    assert purged == 0
    assert AnonymousSession.objects.count() == 1


def test_dry_run_reports_without_deleting() -> None:
    _make_session(age_days=400)
    purged = purge_anonymous_sessions(now=timezone.now(), dry_run=True)
    assert purged == 1
    assert AnonymousSession.objects.count() == 1  # reported, not deleted


def test_command_runs_and_purges() -> None:
    _make_session(age_days=400)
    call_command("purge_expired_data")
    assert AnonymousSession.objects.count() == 0


def test_run_retention_sweep_exposes_categories() -> None:
    assert "anonymous_sessions" in run_retention_sweep(dry_run=True)
