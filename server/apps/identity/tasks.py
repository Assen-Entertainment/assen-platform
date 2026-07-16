"""Periodic data-retention sweep task (Codex #19).

Wraps the flag-gated retention registry (apps.identity.retention.run_retention_sweep)
as a Celery task registered in CELERY_BEAT_SCHEDULE (config.settings.base), so the
nightly job and the ``purge_expired_data`` management command share one code path.

FAIL-CLOSED: the sweep only DELETES/BLANKS rows when ``RETENTION_PURGE_ENABLED`` is
True (default False = dry-run, count only), and the withdrawn-account final purge
stays deferred (counted, never deleted) until the 법무 게이트 fixes the statutory
window. Idempotent per class, so the daily cadence is safe to re-run.
"""

from __future__ import annotations

from celery import shared_task

from apps.identity.retention import run_retention_sweep as _run_retention_sweep


@shared_task  # type: ignore[untyped-decorator]  # celery's decorator is untyped
def run_retention_sweep() -> dict[str, int]:
    """Run the retention sweep across every registered class; return per-class counts.

    Delegates to :func:`apps.identity.retention.run_retention_sweep`, which logs
    ``retention.sweep`` per class and executes an implemented purge action only when
    ``RETENTION_PURGE_ENABLED`` is True. Returns ``{class_name: matched_count}``.
    """
    return _run_retention_sweep()
