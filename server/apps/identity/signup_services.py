"""Phone-identity hashing + digital membership card (ASS-98 v0).

Phone-OTP signup was retired in favour of email/social auth (auth redesign); this
module now provides the phone-number canonicalisation + keyed hashing used by the
demo seed and the legacy phone-hash migration, plus the read model for the digital
membership card.

Privacy (Fan_Signup_Privacy_Policy §1): the phone number is hashed and never
stored raw; only ``auth_subject_hash`` and the display-only nickname persist.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass

from django.conf import settings
from django.db import IntegrityError, transaction

from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account
from config.errors import ErrorCode


class SignupError(Exception):
    """Raised when a signup is rejected (bad OTP or missing mandatory consent).

    Carries a stable :class:`~config.errors.ErrorCode` so the API layer can surface a
    machine-readable ``code`` alongside ``detail`` (the web branches on the code, not
    the message). Defaults to :attr:`ErrorCode.PHONE_INVALID` for the phone-format
    guard in :func:`normalize_phone`; callers set a more specific code at each raise.
    """

    def __init__(
        self, message: str, *, code: ErrorCode = ErrorCode.PHONE_INVALID
    ) -> None:
        """Bind the human ``detail`` message and the stable error ``code``."""
        self.code = code
        super().__init__(message)


# Minimum digit count for a plausible phone number. KR mobile numbers are 10-11
# digits; 8 is a permissive floor that still rejects empty/junk input. Full E.164
# validation (libphonenumber) is a later issue.
_MIN_PHONE_DIGITS = 8


def normalize_phone(phone: str) -> str:
    """Canonicalise a phone number to one stable ``+``-prefixed key.

    The ``auth_subject_hash`` — and the dedup/race guarantees that key on it —
    are only as stable as this function: the SAME human number must map to ONE
    string however it was typed. So we drop formatting and fold the Korean
    national form (``010…``) and bare country-coded forms onto a single ``+82…``
    value; otherwise ``01012345678`` and ``+821012345678`` would hash
    differently and create two accounts (two ``fan_signed_up`` events). Empty or
    too-short input is rejected (:class:`SignupError`) so the OTP-send and signup
    paths both refuse junk. Full international validation (libphonenumber) is a
    later issue; this covers the KR P0 surface and keeps non-KR ``+`` forms stable.
    """
    has_plus = phone.strip().startswith("+")
    digits = "".join(ch for ch in phone if ch.isdigit())
    if has_plus:
        core = digits  # already international (e.g. 8210…, 1…)
    elif digits.startswith("0"):
        core = "82" + digits[1:]  # KR national trunk 0 -> +82 country code
    else:
        core = digits  # bare country-coded or foreign digits
    if len(core) < _MIN_PHONE_DIGITS:
        raise SignupError(
            "A valid phone number is required.", code=ErrorCode.PHONE_INVALID
        )
    return "+" + core


def hash_phone(phone: str) -> str:
    """Return the account key derived from a phone number — the only phone-derived
    value stored (the raw number never is).

    A keyed **HMAC-SHA256** (``v1:<base64url>``), not a bare digest: the phone-number
    space is small enough to brute-force a plain SHA-256 offline, so the hash is
    keyed with a dedicated server secret (``PHONE_IDENTIFIER_HMAC_KEY``, separate
    from ``SECRET_KEY``) — a stolen DB alone can no longer enumerate numbers
    (ASS-287 A-2). Still pseudonymous PII, not anonymisation. Callers pass an
    already-:func:`normalize_phone`d value; rows created before A-2 (bare SHA-256)
    are migrated in place on access (:func:`migrate_legacy_subject_hash`).
    """
    mac = hmac.new(_phone_hmac_key(), phone.encode("utf-8"), hashlib.sha256).digest()
    return "v1:" + base64.urlsafe_b64encode(mac).rstrip(b"=").decode("ascii")


def _phone_hmac_key() -> bytes:
    """The dedicated phone-identifier HMAC key, or fail closed (never unkeyed).

    Production requires a real >=32-byte key at boot (config.settings.prod);
    dev/test carry an insecure default. This runtime guard is defence in depth so a
    misconfigured environment can never fall back to an unkeyed/short-keyed hash.

    ⚠️ ROTATION IS A BREAKING MIGRATION. Changing this key changes every ``v1:``
    hash, so every existing account's login lookup would miss and a re-signup would
    mint a duplicate (the unique constraint does not even fire — the values differ).
    :func:`migrate_legacy_subject_hash` only rekeys the pre-A-2 *bare SHA-256* rows,
    NOT rows keyed by a previous key's ``v1``. Rotating safely requires a ``v2``
    dual-read (compute v2, then rekey from the previous key's v1) before the swap;
    until that exists, treat the key as immutable and hold it in a KMS/secret
    manager (security review 2026-07-11).
    """
    key = settings.PHONE_IDENTIFIER_HMAC_KEY
    key_bytes = key.encode("utf-8") if isinstance(key, str) else key
    # Byte length (not code-point count) — the requirement is >= 32 bytes of key.
    if not key_bytes or len(key_bytes) < 32:
        raise RuntimeError(
            "PHONE_IDENTIFIER_HMAC_KEY is not configured (must be >= 32 bytes)."
        )
    return key_bytes


def _legacy_phone_hash(phone: str) -> str:
    """The pre-A-2 bare SHA-256 key — used ONLY to find and rekey legacy rows."""
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


def migrate_legacy_subject_hash(phone: str) -> None:
    """Rekey a pre-A-2 (bare SHA-256) account row to the v1 HMAC hash, in place.

    Dual-read migration: rows created before A-2 are keyed by ``SHA-256(phone)``;
    new logins/signups key by the v1 HMAC. On access we rekey the legacy row so the
    caller then finds it under the v1 hash — no duplicate account and no lock-out.
    A no-op when there is no legacy row, or when the v1 row already exists. ``phone``
    must already be :func:`normalize_phone`d (as at both call sites).
    """
    v1 = hash_phone(phone)
    if Account.objects.filter(auth_subject_hash=v1).exists():
        return
    try:
        with transaction.atomic():
            Account.objects.filter(auth_subject_hash=_legacy_phone_hash(phone)).update(
                auth_subject_hash=v1
            )
    except IntegrityError:
        # A concurrent request rekeyed it first — the caller finds the v1 row.
        pass


@dataclass(frozen=True)
class MembershipCard:
    """Digital membership card read model (no PII beyond the display nickname)."""

    nickname: str
    member_id: str
    visit_count: int
    points: int
    coupons: int


def membership_card(account: Account) -> MembershipCard:
    """Build the digital membership card read model for [account].

    ``visit_count`` is the fan's valid check-ins from the event ledger; points
    and coupons are placeholders (their domains are separate issues — ASS-98
    P0 excludes 등급제/유료 멤버십).
    """
    # Exclude operator-voided visits: the append-only ledger keeps the original
    # check-in row, so a void is a separate visit_invalidated event (mirrors
    # count_msfc_starts) — without this an annulled visit still shows on the card.
    invalidated_visit_ids = EventRecord.objects.filter(
        event_name=EventName.VISIT_INVALIDATED.value,
    ).values("visit_id")
    visit_count = (
        EventRecord.objects.filter(
            event_name=EventName.VISIT_CHECKED_IN.value,
            fan_id=str(account.fan_id),
            is_invalidated=False,
        )
        .exclude(visit_id__in=invalidated_visit_ids)
        .count()
    )
    return MembershipCard(
        nickname=account.nickname,
        member_id=str(account.fan_id),
        visit_count=visit_count,
        points=0,
        coupons=0,
    )
