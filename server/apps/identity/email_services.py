"""Email + password fan auth (the email counterpart of ``register_fan``).

Additive to phone OTP / social login (ASS-98): turns an email + password + mandatory
consent into a fan :class:`~apps.identity.models.Account`, sends a (mock) verification
mail, and — only after the fan confirms the link — issues a token pair via the
**unchanged** token core. Email verification is required before login.

Identity model: an email account keys on ``Account.email`` (plaintext EmailField +
the ``uniq_fan_email`` partial unique), NOT on a hashed ``auth_subject_hash`` — email
must be stored raw to deliver the mail, so a redundant HMAC key would add no privacy.
The fan password reuses the existing ``Account.password_hash`` (Django's configured
hasher via :func:`make_password`), the same field staff logins use.

Privacy: email is raw PII kept only to send mail; it is cleared on withdrawal
(:func:`apps.identity.services.withdraw_account`). Consent (terms/privacy + 만 14세)
is mandatory on first signup, exactly as phone/social.
"""

from __future__ import annotations

from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.db import transaction
from django.utils import timezone

from apps.consent.models import ConsentKind
from apps.consent.services import record_consent, set_marketing_consent
from apps.consent.versions import consent_doc_version
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import emit_event
from apps.identity.models import Account, Role
from apps.identity.services import IssuedTokenPair, issue_token_pair
from apps.identity.signup_services import SignupError
from config.email import (
    EmailSender,
    load_verification_token,
    make_verification_token,
)
from config.errors import ErrorCode

# Minimum fan password length (enforced at the wire by the endpoint schema; this floor
# is the service-side guard for direct/test callers).
MIN_PASSWORD_LENGTH = 8


class EmailVerificationError(Exception):
    """Raised when a verify-email token is forged, malformed, or expired.

    A single opaque error so the confirm endpoint returns one 400 without revealing
    whether the token was expired vs forged vs pointed at a missing account.
    """


def normalize_email(email: str) -> str:
    """Canonicalise an email to one stable lookup/uniqueness key.

    Lowercased + stripped so the ``uniq_fan_email`` constraint and the login lookup
    agree regardless of how the address was typed (providers treat the mailbox
    case-insensitively in practice). Empty input is left to the caller's validation.
    """
    return email.strip().lower()


@transaction.atomic
def register_fan_email(
    *,
    email: str,
    password: str,
    nickname: str,
    consent_terms: bool,
    consent_privacy: bool,
    email_sender: EmailSender,
    age_over_14: bool = False,
    marketing_consent: bool = False,
    version: str | None = None,
) -> tuple[Account, str]:
    """Create (or reuse an unverified) email account, record consent, send verify mail.

    Rejects missing terms/privacy consent, an unconfirmed 만 14세 floor, and a too-short
    password (the same mandatory gates as phone signup). A duplicate **verified** email
    is refused (``EMAIL_ALREADY_REGISTERED``); a duplicate **unverified** one is reused
    — password/nickname updated and a fresh verification re-sent — so a fan who never
    confirmed can retry without being permanently blocked by their own abandoned row.
    Returns the account and the signed verification token (the endpoint echoes the
    token only under the dev flag). NO token pair is issued here — the fan is logged in
    on verify, not on signup.
    """
    if not (consent_terms and consent_privacy):
        raise SignupError(
            "Both terms and privacy consent are required.",
            code=ErrorCode.CONSENT_REQUIRED,
        )
    if not age_over_14:
        raise SignupError("만 14세 이상만 가입할 수 있습니다.", code=ErrorCode.UNDERAGE)
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SignupError(
            "비밀번호는 8자 이상이어야 해요.", code=ErrorCode.INVALID_CREDENTIALS
        )
    email = normalize_email(email)

    existing = Account.objects.filter(email=email, role=Role.FAN.value).first()
    if existing is not None and existing.email_verified_at is not None:
        raise SignupError(
            "이미 가입된 이메일이에요.", code=ErrorCode.EMAIL_ALREADY_REGISTERED
        )
    if existing is not None:
        # Reuse the unverified row (idempotent re-signup): refresh credentials + display
        # name and re-send verification instead of tripping uniq_fan_email.
        account = existing
        account.password_hash = make_password(password)
        account.nickname = nickname
        account.save(update_fields=["password_hash", "nickname"])
    else:
        account = Account.objects.create(
            role=Role.FAN.value,
            email=email,
            password_hash=make_password(password),
            nickname=nickname,
            auth_method="email",
        )

    record_consent(
        account=account,
        kind=ConsentKind.TERMS.value,
        version=version or consent_doc_version(ConsentKind.TERMS.value),
    )
    record_consent(
        account=account,
        kind=ConsentKind.PRIVACY.value,
        version=version or consent_doc_version(ConsentKind.PRIVACY.value),
    )
    if marketing_consent:
        # The reachable marketing channel at email signup is email (the fan gave one);
        # false/missing records no opt-in (fail-closed), mirroring register_fan's SMS.
        set_marketing_consent(account=account, channel="email", enabled=True)

    token = make_verification_token(account_id=account.pk, email=account.email)
    email_sender.send_verification(email=account.email, token=token)
    return account, token


def verify_email(*, token: str) -> IssuedTokenPair:
    """Confirm an email-verification token and log the fan in (issue a token pair).

    First confirmation stamps ``email_verified_at`` and emits ``fan_signed_up`` (the
    account only becomes a real fan on verification, so the new-signup KPI counts it
    here, not at the unverified signup). A repeat confirm within the token TTL just
    re-issues tokens (acts as a login link) without a second event. Raises
    :class:`EmailVerificationError` on any bad/expired/mismatched token.
    """
    try:
        account_id, email = load_verification_token(token)
    except signing.BadSignature as exc:
        raise EmailVerificationError("Invalid or expired verification token.") from exc

    account = Account.objects.filter(
        pk=account_id, role=Role.FAN.value, is_active=True
    ).first()
    if account is None or account.email != email:
        raise EmailVerificationError("Invalid or expired verification token.")

    if account.email_verified_at is None:
        account.email_verified_at = timezone.now()
        account.save(update_fields=["email_verified_at"])
        emit_event(
            event_name=EventName.FAN_SIGNED_UP.value,
            occurred_at=timezone.now(),
            actor_type=ActorType.FAN.value,
            source=EventSource.WEB.value,
            fan_id=str(account.fan_id),
            payload={
                "fan_id": str(account.fan_id),
                "signup_method": "web",
                "consent_terms": True,
                "consent_privacy": True,
            },
        )
    return issue_token_pair(account)


def login_email(*, email: str, password: str) -> Account:
    """Authenticate an email + password fan and return the account, or raise.

    Disclosure-minimised: a wrong email and a wrong password both raise
    ``INVALID_CREDENTIALS`` (indistinguishable), mirroring the OTP login. The password
    is checked first, so only a caller who proved the password learns the account is
    unverified (``EMAIL_NOT_VERIFIED`` — required before login), matching how the OTP
    login reveals existence only after the code is proven.
    """
    email = normalize_email(email)
    account = Account.objects.filter(
        email=email, role=Role.FAN.value, is_active=True
    ).first()
    if (
        account is None
        or not account.password_hash
        or not check_password(password, account.password_hash)
    ):
        raise SignupError(
            "이메일 또는 비밀번호가 올바르지 않아요.",
            code=ErrorCode.INVALID_CREDENTIALS,
        )
    if account.email_verified_at is None:
        raise SignupError(
            "이메일 인증이 필요해요.", code=ErrorCode.EMAIL_NOT_VERIFIED
        )
    return account
