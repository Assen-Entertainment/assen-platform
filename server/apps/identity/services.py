"""Token lifecycle and account/merge services (ADR-0002).

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26). Issuance, verification, rotation,
revocation, and refresh-reuse detection live here.

Security properties enforced:
- Plaintext tokens are generated with ``secrets.token_urlsafe(32)`` and returned
  to the caller once; only their SHA-256 hash is stored, so a DB read cannot
  recover a usable token.
- Verification is by hash lookup plus a server-side validity check, so revocation
  and expiry take effect immediately (F11).
- Rotation supersedes the presented refresh token and issues a fresh access +
  refresh pair. Presenting an already-used refresh token revokes the entire
  family (reuse detection), invalidating every token minted in that login.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from apps.identity.models import (
    AccessToken,
    Account,
    RefreshToken,
    Role,
    TokenFamily,
)

# Lifetimes per ADR-0002: access is single-minute-grade short-lived; refresh is
# long enough to keep sessions alive across app use but still bounded.
ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=14)

# Bytes of entropy for each opaque token. 32 bytes (256 bits) is well above
# guessing range; token_urlsafe expands it to a URL-safe string.
_TOKEN_ENTROPY_BYTES = 32


class TokenError(Exception):
    """Raised when a token cannot be verified, rotated, or revoked.

    A single error type keeps auth callers from leaking *why* a token failed
    (expired vs revoked vs reused) to clients, which would aid probing.
    """


@dataclass(frozen=True)
class IssuedTokenPair:
    """The one-time plaintext tokens handed back at login/rotation.

    The plaintext values exist only in this object and the HTTP response; they
    are never stored. ``family_id`` lets callers correlate without the secrets.
    """

    access_token: str
    refresh_token: str
    family_id: int
    access_expires_at: datetime
    refresh_expires_at: datetime


def hash_token(plaintext: str) -> str:
    """Return the SHA-256 hex digest used as the stored token identifier.

    Hashing (not encryption) is correct here: the server only ever needs to
    recognise a presented token, never to recover one.
    """
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _generate_plaintext() -> str:
    """Generate a fresh opaque token string with 256 bits of entropy."""
    return secrets.token_urlsafe(_TOKEN_ENTROPY_BYTES)


def _issue_access_token(family: TokenFamily, *, now: datetime) -> tuple[str, AccessToken]:
    """Create and persist an access token, returning (plaintext, row)."""
    plaintext = _generate_plaintext()
    token = AccessToken.objects.create(
        family=family,
        token_hash=hash_token(plaintext),
        expires_at=now + ACCESS_TOKEN_TTL,
    )
    return plaintext, token


def _issue_refresh_token(family: TokenFamily, *, now: datetime) -> tuple[str, RefreshToken]:
    """Create and persist a refresh token, returning (plaintext, row)."""
    plaintext = _generate_plaintext()
    token = RefreshToken.objects.create(
        family=family,
        token_hash=hash_token(plaintext),
        expires_at=now + REFRESH_TOKEN_TTL,
    )
    return plaintext, token


def issue_token_pair(account: Account) -> IssuedTokenPair:
    """Start a new login: create a token family and an access+refresh pair.

    A login is the root of a family; subsequent rotations extend it. Returns the
    one-time plaintext pair for the caller to deliver to the client.
    """
    now = timezone.now()
    family = TokenFamily.objects.create(account=account)
    access_plain, access = _issue_access_token(family, now=now)
    refresh_plain, refresh = _issue_refresh_token(family, now=now)
    return IssuedTokenPair(
        access_token=access_plain,
        refresh_token=refresh_plain,
        family_id=family.pk,
        access_expires_at=access.expires_at,
        refresh_expires_at=refresh.expires_at,
    )


def verify_access_token(plaintext: str) -> Account:
    """Resolve a presented access token to its account, or raise.

    Looks up by hash and applies the server-side validity check so a revoked or
    expired token is rejected even though its row still exists.
    """
    try:
        token = AccessToken.objects.select_related("family", "family__account").get(
            token_hash=hash_token(plaintext)
        )
    except AccessToken.DoesNotExist as exc:
        raise TokenError("Access token not recognised.") from exc
    if not token.is_valid():
        raise TokenError("Access token is expired or revoked.")
    if not token.family.account.is_active:
        raise TokenError("Account is inactive.")
    return token.family.account


def rotate_refresh_token(plaintext: str) -> IssuedTokenPair:
    """Rotate a refresh token: supersede it and issue a new pair.

    Reuse detection: if the presented token is already used (or its family is
    revoked), this is a replay — revoke the whole family and raise, so a stolen
    refresh token cannot outlive the legitimate client's next rotation.
    """
    try:
        token = RefreshToken.objects.select_related("family", "family__account").get(
            token_hash=hash_token(plaintext)
        )
    except RefreshToken.DoesNotExist as exc:
        raise TokenError("Refresh token not recognised.") from exc

    family = token.family

    # Replay of a consumed token, or use within an already-revoked family, is the
    # reuse signal: burn the family down.
    if token.used or family.revoked:
        if not family.revoked:
            family.revoke(reason="refresh_reuse_detected")
        # Belt and suspenders: also revoke outstanding access tokens now.
        revoke_family(family, reason="refresh_reuse_detected")
        raise TokenError("Refresh token reuse detected; token family revoked.")

    now = timezone.now()
    if token.expires_at <= now:
        raise TokenError("Refresh token is expired.")

    # Consume the presented token and mint a successor pair in the same family.
    token.mark_used()
    access_plain, access = _issue_access_token(family, now=now)
    refresh_plain, refresh = _issue_refresh_token(family, now=now)
    return IssuedTokenPair(
        access_token=access_plain,
        refresh_token=refresh_plain,
        family_id=family.pk,
        access_expires_at=access.expires_at,
        refresh_expires_at=refresh.expires_at,
    )


def revoke_family(family: TokenFamily, *, reason: str) -> None:
    """Revoke a family and all its outstanding access tokens (logout / F11).

    Marking the family revoked stops future rotations; flipping outstanding
    access tokens to revoked stops in-flight access immediately. Refresh tokens
    are gated on ``family.revoked`` so they need no per-row flag.
    """
    if not family.revoked:
        family.revoke(reason=reason)
    AccessToken.objects.filter(family=family, revoked=False).update(revoked=True)


def revoke_all_for_account(account: Account, *, reason: str) -> None:
    """Revoke every token family for an account (e.g. on block).

    Used by safety/RBAC flows that must cut off a principal entirely rather than
    a single session.
    """
    for family in account.token_families.filter(revoked=False):
        revoke_family(family, reason=reason)


def merge_anonymous_into_account(
    *, anonymous_id: str, account: Account
) -> int:
    """Attach an anonymous session to a fan account and link its prior events.

    Delegates event re-attribution to the event-log service so the merge is
    recorded as an ``anonymous_user_merged`` event (the log is append-only and
    cannot be rewritten). Returns the count of prior anonymous events linked, so
    callers/tests can assert the merge connected the expected history without
    double-counting MSFC starts. The ``AnonymousSession`` row, if present, is
    pointed at the account.
    """
    from apps.event_log.services import reattribute_anonymous_events
    from apps.identity.models import AnonymousSession

    AnonymousSession.objects.filter(anonymous_id=anonymous_id).update(
        merged_into=account
    )
    return reattribute_anonymous_events(
        anonymous_id=anonymous_id, fan_id=str(account.fan_id)
    )


def authenticate_operator(*, username: str, password: str) -> Account:
    """Verify operator credentials and return the account, or raise.

    Uses Django's configured password hasher (project standard: PBKDF2; #1/ASS-91
    — no Argon2 dependency is pinned). Restricts login to staff roles so a fan
    row with a blank password cannot be used as an operator login.
    """
    from django.contrib.auth.hashers import check_password

    staff_roles = {Role.OPERATOR.value, Role.MANAGER.value, Role.ADMIN.value}
    try:
        account = Account.objects.get(username=username, is_active=True)
    except Account.DoesNotExist as exc:
        raise TokenError("Invalid operator credentials.") from exc
    if account.role not in staff_roles or not account.password_hash:
        raise TokenError("Invalid operator credentials.")
    if not check_password(password, account.password_hash):
        raise TokenError("Invalid operator credentials.")
    return account
