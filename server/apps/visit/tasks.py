"""Periodic maintenance tasks for the visit domain (ASS-151).

Rotating QR check-in mints a row per refresh (a fan app polling a ~30s QR makes
~120 rows/hour), and the vast majority are never redeemed. Redeemed rows are kept
for audit; unredeemed expired rows have no value and would otherwise grow without
bound on a hot path. This reaper purges them on a schedule (CELERY_BEAT_SCHEDULE).
"""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.visit.models import CheckinToken

# Keep recently-expired unredeemed tokens for a short grace window before
# purging, so a reap can never race a just-completing redemption.
_RETENTION = timedelta(hours=1)


@shared_task  # type: ignore[untyped-decorator]  # celery's decorator is untyped
def purge_expired_checkin_tokens() -> int:
    """Delete unredeemed check-in tokens expired longer than the grace window.

    Redeemed tokens are retained (they are the audit trail of a scan); only
    never-used, long-expired rows are removed. Returns the number deleted.
    """
    cutoff = timezone.now() - _RETENTION
    deleted, _ = CheckinToken.objects.filter(
        redeemed_at__isnull=True, expires_at__lt=cutoff
    ).delete()
    return deleted
