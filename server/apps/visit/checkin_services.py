"""Service layer for rotating QR check-in tokens (ASS-99).

The fan app shows a server-issued rotating QR; an operator scan redeems it into
a real visit. The security model (CONSTRAINTS #18) is: short TTL + single use +
supersede-on-reissue, so a screenshot of yesterday's (or even ten-seconds-ago's)
QR is dead. Redemption delegates the actual visit row to the visit domain
(:func:`record_qr_visit`) so the audit/event coupling stays in one place.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.identity.models import Account
from apps.visit.models import CheckinToken, VisitRecord
from apps.visit.services import record_qr_visit

# CONSTRAINTS #18 rotation band is 15~60s; 30s balances scan latency against the
# screenshot-replay window. Centralised so the API and tests share one value.
_DEFAULT_TTL = timedelta(seconds=30)


@transaction.atomic
def issue_checkin_token(*, fan: Account, ttl: timedelta = _DEFAULT_TTL) -> CheckinToken:
    """Issue a fresh rotating check-in token for [fan], superseding live ones.

    Rotation means only the *latest* token is valid: any of the fan's earlier
    un-redeemed, unexpired tokens are expired now, so a stale QR screenshot from a
    previous refresh cannot be redeemed even within its original TTL.
    """
    now = timezone.now()
    CheckinToken.objects.filter(
        fan=fan, redeemed_at__isnull=True, expires_at__gt=now
    ).update(expires_at=now)
    return CheckinToken.objects.create(
        fan=fan,
        token=secrets.token_urlsafe(32),
        expires_at=now + ttl,
    )


@transaction.atomic
def redeem_checkin_token(
    *, token: str, operator: Account, store_id: str | None = None
) -> tuple[VisitRecord, CheckinToken]:
    """Validate and redeem [token] (an operator scan) into a fan visit.

    Rejects an unknown, already-redeemed (replay), or expired (rotation) token
    with a ``ValueError`` the API maps to 400. On success it records the visit
    via the visit domain and marks the token redeemed (single use). The row is
    locked for update so two concurrent scans cannot both redeem it.
    """
    now = timezone.now()
    try:
        entry = (
            CheckinToken.objects.select_for_update()
            .select_related("fan")
            .get(token=token)
        )
    except CheckinToken.DoesNotExist as exc:
        raise ValueError("Invalid check-in token.") from exc
    if entry.redeemed_at is not None:
        raise ValueError("Check-in token already redeemed.")
    if entry.expires_at <= now:
        raise ValueError("Check-in token expired.")

    record = record_qr_visit(
        fan=entry.fan,
        visited_at=now,
        operator=operator,
        store_id=store_id,
    )
    entry.redeemed_at = now
    entry.redeemed_by = operator
    entry.visit = record
    entry.save(update_fields=["redeemed_at", "redeemed_by", "visit"])
    return record, entry
