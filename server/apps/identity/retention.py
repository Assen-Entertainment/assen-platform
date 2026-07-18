"""Data-retention sweep (D2/D6, privacy decisions 2026-07-12; Codex #19).

Legal-minimum retention: data whose purpose is spent is purged; only legally
mandated records are held for their statutory window. This module holds the
declarative *retention registry* the ``purge_expired_data`` command and the
``apps.identity.tasks.run_retention_sweep`` Celery task both run (nightly in
production). See docs/ops/privacy-retention-consent-decisions-2026-07-12.md §2.

FAIL-CLOSED SKELETON (Codex #19, 법무 게이트 PENDING). The sweep always COUNTS the
rows past each class's window and logs ``retention.sweep``, but it only executes a
class's purge action when the master switch ``settings.RETENTION_PURGE_ENABLED`` is
True (default False = dry-run) AND that class's action is implemented. So with the
default flag OFF nothing is ever deleted or blanked — the policy is encoded and
scheduled, but activation waits on legal.

Retention classes (registered in :data:`RETENTION_CLASSES`):

- **anonymous_sessions** — unmerged :class:`AnonymousSession` stubs older than
  :data:`ANON_SESSION_RETENTION` (1 year). These carry no PII (a random
  ``anonymous_id`` UUID); deleting them is pure minimisation. *Implemented* (deletes
  when the flag is on).
- **withdrawn_accounts** — already-anonymised :class:`Account` rows (``withdrawn_at``
  set) older than ``RETENTION_WITHDRAWN_ACCOUNT_DAYS``. The purge action is the
  DEFERRED final파기: *not implemented* — the sweep counts it but never deletes the
  row, because withdrawal already performed the privacy-critical anonymisation and
  the statutory hold window is a 법무 게이트. Wired to actually delete once legal
  signs off.
- **expired_token_families** — fully expired/revoked :class:`TokenFamily` rows older
  than ``RETENTION_TOKEN_DAYS``. Pure auth-state hygiene (no PII); *implemented*.
- **order_shipping_snapshots** — COMPLETED/CANCELLED :class:`Order` rows older than
  ``RETENTION_SHIPPING_SNAPSHOT_DAYS``. The action BLANKS the ``recipient_*`` /
  ``postal_code`` / ``address*`` delivery-address snapshot; the order ROW is kept
  (its amounts/line items remain the transaction record). *Implemented*.

Access-log retention (접속·보안 로그 3개월) stays an INFRASTRUCTURE concern — there is
no DB access-log table (the event_log ledger is immutable and stores no IP), so it is
configured on the log sink (Sentry / CloudWatch), not swept here.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.commerce.models import Order, OrderStatus
from apps.identity.models import (
    AccessToken,
    Account,
    AnonymousSession,
    RefreshToken,
    TokenFamily,
)

logger = logging.getLogger(__name__)

# Unmerged anonymous (pre-signup) sessions are abandoned after this window.
ANON_SESSION_RETENTION = timedelta(days=365)


# --- Per-class queryset builders (rows past their window still needing action) ------


def _anonymous_sessions_qs(now: datetime) -> QuerySet[AnonymousSession]:
    """Unmerged :class:`AnonymousSession` stubs older than the retention window."""
    cutoff = now - ANON_SESSION_RETENTION
    return AnonymousSession.objects.filter(
        merged_into__isnull=True, created_at__lt=cutoff
    )


def _withdrawn_accounts_qs(now: datetime) -> QuerySet[Account]:
    """Anonymised withdrawn :class:`Account` rows older than the retention window."""
    cutoff = now - timedelta(days=settings.RETENTION_WITHDRAWN_ACCOUNT_DAYS)
    return Account.objects.filter(withdrawn_at__isnull=False, withdrawn_at__lt=cutoff)


def _expired_token_families_qs(now: datetime) -> QuerySet[TokenFamily]:
    """Fully expired/revoked :class:`TokenFamily` rows older than the retention window.

    A family is eligible when it is past the window AND no longer usable — either it
    is revoked, or it holds no still-valid token (no unexpired non-revoked access
    token and no unexpired unused refresh token). Deleting the family cascades to its
    tokens (``on_delete=CASCADE``).
    """
    cutoff = now - timedelta(days=settings.RETENTION_TOKEN_DAYS)
    live_access = AccessToken.objects.filter(
        family=OuterRef("pk"), revoked=False, expires_at__gt=now
    )
    live_refresh = RefreshToken.objects.filter(
        family=OuterRef("pk"), used=False, expires_at__gt=now
    )
    return TokenFamily.objects.filter(created_at__lt=cutoff).filter(
        Q(revoked=True) | (~Exists(live_access) & ~Exists(live_refresh))
    )


def _order_shipping_snapshots_qs(now: datetime) -> QuerySet[Order]:
    """Terminal :class:`Order` rows past the window that still carry a recipient snapshot.

    Age is measured from ``completed_at`` when set (fulfillment work), else
    ``created_at`` (e.g. a CANCELLED order that never completed). Rows whose
    ``recipient_*`` snapshot is already fully blank are excluded so the blanking
    action is idempotent (a second sweep finds nothing to do).
    """
    cutoff = now - timedelta(days=settings.RETENTION_SHIPPING_SNAPSHOT_DAYS)
    return (
        Order.objects.filter(
            status__in=(OrderStatus.COMPLETED.value, OrderStatus.CANCELLED.value)
        )
        .annotate(_terminal_at=Coalesce("completed_at", "created_at"))
        .filter(_terminal_at__lt=cutoff)
        .exclude(
            recipient_name="",
            recipient_phone="",
            postal_code="",
            address1="",
            address2="",
        )
    )


# --- Per-class purge actions --------------------------------------------------------


def _delete_queryset(queryset: QuerySet[Any]) -> int:
    """Delete every matched row; return the number of rows deleted."""
    deleted, _ = queryset.delete()
    return deleted


def _blank_order_snapshots(queryset: QuerySet[Order]) -> int:
    """Blank the delivery-address snapshot on each order; keep the order row.

    Only the recipient PII fields are cleared — amounts, status and line items (the
    transaction record) are untouched. Returns the number of orders updated.
    """
    return queryset.update(
        recipient_name="",
        recipient_phone="",
        postal_code="",
        address1="",
        address2="",
    )


def _purge_withdrawn_accounts_deferred(queryset: QuerySet[Account]) -> int:
    """DEFERRED final purge of anonymised withdrawn accounts — NOT implemented.

    The registry marks ``withdrawn_accounts`` as unimplemented so the sweep never
    reaches this action; it exists as the single, documented home for the deletion
    once 법무 fixes the statutory hold window. Raising keeps the skeleton honest: if
    the class is ever flipped to implemented without wiring a real purge, the sweep
    fails loudly instead of silently deleting on an unapproved window.
    """
    raise NotImplementedError(
        "withdrawn-account final purge is deferred pending the 법무 게이트 "
        "(statutory hold window). See apps.identity.retention module docstring."
    )


# --- Retention registry -------------------------------------------------------------


@dataclass(frozen=True)
class RetentionClass:
    """One retention policy: rows past a window plus the action that clears them.

    ``match_queryset(now)`` returns the rows currently past their retention window
    (already-purged rows excluded, so counts are idempotent). ``purge(queryset)``
    performs the clearing action and returns the number of rows affected.
    ``implemented`` is False for a DEFERRED action: the sweep counts its matches but
    never runs ``purge`` — the real action is wired once legal approves the window.
    """

    name: str
    match_queryset: Callable[[datetime], QuerySet[Any]]
    purge: Callable[[QuerySet[Any]], int]
    implemented: bool


RETENTION_CLASSES: tuple[RetentionClass, ...] = (
    RetentionClass(
        name="anonymous_sessions",
        match_queryset=_anonymous_sessions_qs,
        purge=_delete_queryset,
        implemented=True,
    ),
    RetentionClass(
        name="withdrawn_accounts",
        match_queryset=_withdrawn_accounts_qs,
        purge=_purge_withdrawn_accounts_deferred,
        implemented=False,
    ),
    RetentionClass(
        name="expired_token_families",
        match_queryset=_expired_token_families_qs,
        purge=_delete_queryset,
        implemented=True,
    ),
    RetentionClass(
        name="order_shipping_snapshots",
        match_queryset=_order_shipping_snapshots_qs,
        purge=_blank_order_snapshots,
        implemented=True,
    ),
)


# --- Public entry points ------------------------------------------------------------


def purge_anonymous_sessions(*, now: datetime, dry_run: bool = False) -> int:
    """Delete unmerged :class:`AnonymousSession` rows older than the retention window.

    Standalone helper retained for direct/targeted use: a merged session is kept (it
    is linked to a live account's history); only never-merged stubs past
    :data:`ANON_SESSION_RETENTION` are purged. Ignores the master switch (an explicit
    call means the caller intends the purge). Returns the number of rows purged (or
    that *would* be purged when ``dry_run``).
    """
    queryset = _anonymous_sessions_qs(now)
    count = queryset.count()
    if not dry_run and count:
        queryset.delete()
    return count


def run_retention_sweep(*, dry_run: bool = False) -> dict[str, int]:
    """Run every registered retention class; return ``{class_name: matched_count}``.

    For each class the rows past its window are COUNTED and logged (``retention.sweep``).
    A class's purge action runs only when ``settings.RETENTION_PURGE_ENABLED`` is True,
    ``dry_run`` is False, and the class is implemented — so the default (flag off)
    leaves the database untouched. Safe to run repeatedly: implemented classes exclude
    already-purged rows, so a second run finds nothing to do.
    """
    now = timezone.now()
    purge_enabled: bool = settings.RETENTION_PURGE_ENABLED
    result: dict[str, int] = {}
    for retention_class in RETENTION_CLASSES:
        queryset = retention_class.match_queryset(now)
        matched = queryset.count()
        execute = purge_enabled and not dry_run and retention_class.implemented
        purged = retention_class.purge(queryset) if (execute and matched) else 0
        logger.info(
            "retention.sweep",
            extra={
                "retention_class": retention_class.name,
                "matched": matched,
                "purged": purged,
                "executed": execute,
                "deferred": not retention_class.implemented,
            },
        )
        result[retention_class.name] = matched
    return result
