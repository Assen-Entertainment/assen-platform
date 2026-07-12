"""Data-retention sweep (D2/D6, privacy decisions 2026-07-12).

Legal-minimum retention: data whose purpose is spent is purged; only legally
mandated records are held for their statutory window. This module holds the
sweep logic the ``purge_expired_data`` management command runs (nightly in
production). See docs/ops/privacy-retention-consent-decisions-2026-07-12.md §2.

Concrete purge implemented now:
- **Abandoned pre-signup identities** — ``AnonymousSession`` rows that were never
  merged into a fan account and are older than :data:`ANON_SESSION_RETENTION`
  (1 year). These stubs carry no PII (a random ``anonymous_id`` UUID), so this is
  pure minimisation of stale rows.

Documented but intentionally NOT swept in code (no aged data exists yet):
- **접속·보안 로그(로그인 IP 등) 3개월** — there is NO database access-log table:
  the event_log ledger is immutable and stores no IP, and ``AuditEntry`` records
  privileged staff actions without IP. Access-log retention is therefore an
  INFRASTRUCTURE concern — configure a 3-month retention on the application log
  sink (Sentry / CloudWatch), not a DB purge here.
- **거래·분쟁 기록 5년/3년 + 익명화된 탈퇴 계정의 최종 파기** — real payments and
  shipping are still mock/gated, so no transaction record has reached the
  전자상거래법 5년/3년 window, and no withdrawn account (already anonymised at
  withdrawal — see :func:`apps.identity.services.withdraw_account`) has aged past
  the 5-year hold. These are wired once real transaction data exists and the
  Order/Subscription↔Account retention linkage is finalised; withdrawal already
  performs the privacy-critical step (immediate anonymisation), so this remaining
  purge is cleanup of already-anonymised rows, not a pending exposure.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from apps.identity.models import AnonymousSession

# Unmerged anonymous (pre-signup) sessions are abandoned after this window.
ANON_SESSION_RETENTION = timedelta(days=365)


def purge_anonymous_sessions(*, now: datetime, dry_run: bool = False) -> int:
    """Delete unmerged :class:`AnonymousSession` rows older than the retention window.

    A merged session is kept (it is linked to a live account's history); only
    never-merged stubs past :data:`ANON_SESSION_RETENTION` are purged. Returns the
    number of rows purged (or that *would* be purged when ``dry_run``).
    """
    cutoff = now - ANON_SESSION_RETENTION
    stale = AnonymousSession.objects.filter(
        merged_into__isnull=True, created_at__lt=cutoff
    )
    count = stale.count()
    if not dry_run and count:
        stale.delete()
    return count


def run_retention_sweep(*, dry_run: bool = False) -> dict[str, int]:
    """Run every retention purge and return per-category counts.

    Currently a single concrete category (``anonymous_sessions``); structured as a
    dict so more categories can be added without changing the command contract.
    """
    now = timezone.now()
    return {
        "anonymous_sessions": purge_anonymous_sessions(now=now, dry_run=dry_run),
    }
