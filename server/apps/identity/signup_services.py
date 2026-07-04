"""Fan signup + digital membership card (ASS-98 v0).

The approved provider is phone OTP (Company-OS
``20_Operations/Fan_Signup_Privacy_Policy.md``). This service turns a verified
phone OTP plus mandatory terms/privacy consent into a fan
:class:`~apps.identity.models.Account` (merging any prior anonymous activity),
records the consents, emits ``fan_signed_up``, and returns a token pair via the
**unchanged** token core. It also exposes the read model for the digital
membership card.

Privacy (Fan_Signup_Privacy_Policy §1): the phone number is hashed and never
stored raw; only ``auth_subject_hash`` and the display-only nickname persist.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.consent.models import ConsentKind
from apps.consent.services import record_consent
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.models import EventRecord
from apps.event_log.services import emit_event
from apps.identity.models import Account, Role
from apps.identity.services import (
    IssuedTokenPair,
    issue_token_pair,
    merge_anonymous_into_account,
)
from config.errors import ErrorCode
from config.otp import OtpSender

# Consent wording version recorded at signup. The final copy is human-approved;
# storing the version lets the gate require re-consent when the wording changes.
SIGNUP_CONSENT_VERSION = "1.0"


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
    """Return the SHA-256 of a phone number — the only phone-derived value stored."""
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MembershipCard:
    """Digital membership card read model (no PII beyond the display nickname)."""

    nickname: str
    member_id: str
    visit_count: int
    points: int
    coupons: int


@transaction.atomic
def register_fan(
    *,
    phone: str,
    nickname: str,
    consent_terms: bool,
    consent_privacy: bool,
    otp_code: str,
    otp_sender: OtpSender,
    anonymous_id: str = "",
    version: str = SIGNUP_CONSENT_VERSION,
) -> IssuedTokenPair:
    """Register (or re-attach) a fan from a verified phone OTP and consent.

    Rejects a bad OTP and missing terms/privacy consent (both mandatory —
    Fan_Signup_Privacy_Policy §5). Reuses an existing fan with the same phone
    (hash match) so a re-signup merges rather than duplicates, folds in any
    anonymous activity, records both consents, emits ``fan_signed_up`` on first
    creation only (a re-signup must not re-emit), and returns a fresh token pair
    from the unchanged token core.
    """
    if not (consent_terms and consent_privacy):
        raise SignupError(
            "Both terms and privacy consent are required.",
            code=ErrorCode.CONSENT_REQUIRED,
        )
    phone = normalize_phone(phone)
    if not otp_sender.verify(phone=phone, code=otp_code):
        raise SignupError("Invalid OTP.", code=ErrorCode.OTP_INVALID)

    subject_hash = hash_phone(phone)
    # get_or_create wraps the INSERT in a savepoint, so a concurrent signup that
    # loses the uniq_fan_auth_subject race surfaces as IntegrityError and is
    # retried as a fetch — no duplicate fan, and the outer atomic stays usable.
    account, created = Account.objects.get_or_create(
        auth_subject_hash=subject_hash,
        role=Role.FAN.value,
        defaults={"nickname": nickname, "auth_method": "phone"},
    )
    if not created and nickname and account.nickname != nickname:
        account.nickname = nickname  # latest nickname wins on re-signup
        account.save(update_fields=["nickname"])

    if anonymous_id:
        merge_anonymous_into_account(anonymous_id=anonymous_id, account=account)

    record_consent(account=account, kind=ConsentKind.TERMS.value, version=version)
    record_consent(account=account, kind=ConsentKind.PRIVACY.value, version=version)

    if created:
        # fan_signed_up marks a NEW fan account and feeds the ASS-112 new-signup
        # KPI. Re-signup / concurrent double-submit returns the existing account
        # (created=False) and must NOT re-emit, or the append-only ledger would
        # permanently inflate the signup count (a re-signup is a re-auth, not a
        # new fan). The fresh token pair below is still issued every time.
        emit_event(
            event_name=EventName.FAN_SIGNED_UP.value,
            occurred_at=timezone.now(),
            actor_type=ActorType.FAN.value,
            source=EventSource.WEB.value,
            fan_id=str(account.fan_id),
            payload={
                "fan_id": str(account.fan_id),
                # Data_Event_Schema signup_method domain is qr/web/admin/import
                # (signup *channel*); the OTP provider lives on Account.auth_method.
                "signup_method": "web",
                "consent_terms": consent_terms,
                "consent_privacy": consent_privacy,
            },
        )
    return issue_token_pair(account)


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
