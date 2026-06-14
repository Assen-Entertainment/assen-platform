"""Service layer for rotating QR check-in tokens (ASS-99).

The fan app shows a server-issued rotating QR; an operator scan redeems it into
a real visit. The security model (CONSTRAINTS #18) is: short TTL + single use +
supersede-on-reissue, so a screenshot of an earlier QR is dead. The bearer token
is stored only as a SHA-256 hash (the plaintext is returned once), and issuance
is serialised + role-gated. Redemption delegates the visit row to the visit
domain (:func:`record_qr_visit`) so the audit/event coupling stays in one place,
and refuses a fan who is actively blocked from store visits (safety).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.identity.models import Account, Role
from apps.safety.models import BlockScope
from apps.safety.services import has_active_block
from apps.visit.models import CheckinToken, VisitRecord
from apps.visit.services import record_qr_visit

# CONSTRAINTS #18 rotation band is 15~60s; 30s balances scan latency against the
# screenshot-replay window. Centralised so the API and tests share one value.
_DEFAULT_TTL = timedelta(seconds=30)

# Issuance throttle (ASS-151): the fan app refreshes its QR about once per
# rotation window (~25-30s), so a few requests per minute is normal; a tighter
# loop is abuse. Cap issues per fan per window (counted by issued_at, best-effort).
_ISSUE_WINDOW = timedelta(seconds=60)
_ISSUE_MAX = 6


class CheckinThrottled(Exception):
    """Raised when a fan requests check-in tokens faster than the issue cap."""


def _hash_token(raw: str) -> str:
    """Hash a bearer token for storage/lookup; the plaintext is never persisted."""
    return hashlib.sha256(raw.encode()).hexdigest()


@transaction.atomic
def issue_checkin_token(
    *, fan: Account, ttl: timedelta = _DEFAULT_TTL
) -> tuple[CheckinToken, str]:
    """Issue a fresh rotating token for [fan]; return ``(row, plaintext)``.

    The plaintext is returned once for the fan to render as a QR and is never
    stored (only its hash). Rotation means only the *latest* token is valid: the
    fan's earlier un-redeemed, unexpired tokens are expired now. The fan row is
    locked first so two concurrent issues cannot both expire-then-create and
    leave two live tokens.
    """
    if fan.role != Role.FAN.value:
        raise ValueError("Only fans can be issued a check-in token.")
    now = timezone.now()
    # Throttle abusive tight loops without breaking the normal ~30s refresh.
    if (
        CheckinToken.objects.filter(
            fan=fan, issued_at__gte=now - _ISSUE_WINDOW
        ).count()
        >= _ISSUE_MAX
    ):
        raise CheckinThrottled("Too many check-in token requests; slow down.")
    # Serialise concurrent issues for this fan (the one-live-token invariant).
    Account.objects.select_for_update().get(pk=fan.pk)
    CheckinToken.objects.filter(
        fan=fan, redeemed_at__isnull=True, expires_at__gt=now
    ).update(expires_at=now)
    raw = secrets.token_urlsafe(32)
    token = CheckinToken.objects.create(
        fan=fan,
        token_hash=_hash_token(raw),
        expires_at=now + ttl,
    )
    return token, raw


@transaction.atomic
def redeem_checkin_token(
    *, token: str, operator: Account
) -> tuple[VisitRecord, CheckinToken]:
    """Validate and redeem [token] (an operator scan) into a fan visit.

    Rejects (``ValueError`` → API 400) an unknown, already-redeemed (replay), or
    expired (rotation) token; a token not bound to a fan (defence in depth); and
    a fan with an active store-visit block (safety — a blocked fan must not
    produce an MSFC visit). On success it records the visit via the visit domain
    and marks the token redeemed (single use). The row is locked for update so
    two concurrent scans cannot both redeem it.
    """
    now = timezone.now()
    try:
        entry = (
            CheckinToken.objects.select_for_update()
            .select_related("fan")
            .get(token_hash=_hash_token(token))
        )
    except CheckinToken.DoesNotExist as exc:
        raise ValueError("Invalid check-in token.") from exc
    if entry.redeemed_at is not None:
        raise ValueError("Check-in token already redeemed.")
    if entry.expires_at <= now:
        raise ValueError("Check-in token expired.")
    if entry.fan.role != Role.FAN.value:
        raise ValueError("Check-in token is not bound to a fan account.")
    if has_active_block(target=entry.fan, scopes=[BlockScope.STORE_VISIT.value]):
        raise ValueError("Fan is blocked from store check-in.")

    record = record_qr_visit(fan=entry.fan, visited_at=now, operator=operator)
    entry.redeemed_at = now
    entry.redeemed_by = operator
    entry.visit = record
    entry.save(update_fields=["redeemed_at", "redeemed_by", "visit"])
    return record, entry
