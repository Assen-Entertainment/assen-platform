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

from django.db import transaction
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
    # Family-level gate: revoke_family()의 per-row 벌크 업데이트와 회전이 경합하면
    # 소각 이후 생성된 access 행이 revoked=False로 남을 수 있다 — 쓰기 순서와 무관하게
    # 소각된 family의 access는 여기서 전부 차단한다.
    if token.family.revoked:
        raise TokenError("Access token family is revoked.")
    if not token.family.account.is_active:
        raise TokenError("Account is inactive.")
    return token.family.account


def rotate_refresh_token(plaintext: str) -> IssuedTokenPair:
    """Rotate a refresh token: supersede it and issue a new pair.

    Reuse detection: if the presented token is already used (or its family is
    revoked), this is a replay — revoke the whole family and raise, so a stolen
    refresh token cannot outlive the legitimate client's next rotation.

    Concurrency (A1): the token is consumed by a *conditional* UPDATE
    (``... WHERE used = FALSE``) inside a transaction, so two rotations racing on
    the same refresh token cannot both mint a successor pair — exactly one wins
    the update; the loser sees ``rowcount == 0`` and is treated as reuse. The
    conditional consume and the successor-pair issuance share one
    ``transaction.atomic`` block so a half-rotation can never be observed. The
    reuse *burn* is done OUTSIDE that block on purpose: it is a durable side effect
    that must survive the ``TokenError`` we raise, and anything inside the atomic
    block would roll back with the exception.
    """
    try:
        token = RefreshToken.objects.select_related("family", "family__account").get(
            token_hash=hash_token(plaintext)
        )
    except RefreshToken.DoesNotExist as exc:
        raise TokenError("Refresh token not recognised.") from exc

    family = token.family

    # Replay of a consumed token, or use within an already-revoked family, is the
    # reuse signal (observed on the snapshot we just read): burn the family down.
    if token.used or family.revoked:
        revoke_family(family, reason="refresh_reuse_detected")
        raise TokenError("Refresh token reuse detected; token family revoked.")

    now = timezone.now()
    if token.expires_at <= now:
        raise TokenError("Refresh token is expired.")

    access_plain: str | None = None
    access: AccessToken | None = None
    refresh_plain: str | None = None
    refresh: RefreshToken | None = None
    with transaction.atomic():
        # Atomically claim the token: only the writer whose UPDATE matches an
        # unused row proceeds. A stale snapshot that passed the check above but
        # lost the race here reports 0 rows and falls through to the burn below.
        consumed = RefreshToken.objects.filter(pk=token.pk, used=False).update(
            used=True, used_at=now
        )
        if consumed:
            access_plain, access = _issue_access_token(family, now=now)
            refresh_plain, refresh = _issue_refresh_token(family, now=now)

    if not consumed:
        # Lost the race to a concurrent rotation of the same token → reuse. Burn
        # the family here (its own autocommit) so the revocation persists past the
        # error we raise.
        revoke_family(family, reason="refresh_reuse_detected")
        raise TokenError("Refresh token reuse detected; token family revoked.")

    assert access is not None and refresh is not None  # set when consumed is truthy
    return IssuedTokenPair(
        access_token=access_plain,  # type: ignore[arg-type]
        refresh_token=refresh_plain,  # type: ignore[arg-type]
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


def revoke_family_for_access(plaintext: str) -> None:
    """Revoke the token family behind a presented access token (logout).

    Looks the access token up by hash and revokes its whole family, so the access
    token and the paired refresh lineage die together (F11). An unrecognised token
    is a silent no-op: logout is idempotent and must not reveal whether a token
    existed. The plaintext is never logged.
    """
    try:
        token = AccessToken.objects.select_related("family").get(
            token_hash=hash_token(plaintext)
        )
    except AccessToken.DoesNotExist:
        return
    revoke_family(token.family, reason="logout")


def revoke_family_for_refresh(plaintext: str) -> None:
    """Revoke the token family behind a presented refresh token (logout).

    The web logout path (A2) may reach the server with only the refresh cookie —
    the short-lived access cookie can have expired while the refresh lineage is
    still live. Revoking the family off the refresh token kills that lineage too,
    so a best-effort logout still ends the session (F11). Like
    :func:`revoke_family_for_access`, an unrecognised token is a silent no-op
    (logout is idempotent and must not reveal whether a token existed); the
    plaintext is never logged.
    """
    try:
        token = RefreshToken.objects.select_related("family").get(
            token_hash=hash_token(plaintext)
        )
    except RefreshToken.DoesNotExist:
        return
    revoke_family(token.family, reason="logout")


def revoke_all_for_account(account: Account, *, reason: str) -> None:
    """Revoke every token family for an account (e.g. on block).

    Used by safety/RBAC flows that must cut off a principal entirely rather than
    a single session.
    """
    for family in account.token_families.filter(revoked=False):
        revoke_family(family, reason=reason)


@transaction.atomic
def withdraw_account(account: Account) -> None:
    """Withdraw (탈퇴) a fan account: anonymise, offboard, and end every session.

    Privacy decisions 2026-07-12 (D3 — 즉시 익명화). On withdrawal the account's PII
    is cleared immediately: the display ``nickname`` and the phone-derived
    ``auth_subject_hash`` are emptied and ``is_active`` is set False. The row itself
    is **kept, not deleted**, so orders/subscriptions/events that reference
    ``fan_id`` retain FK integrity under the now-anonymised id (legal-hold records
    stay linked to a pseudonymous token, not to a person). Every token family is
    revoked so all sessions end at once, and clearing ``auth_subject_hash`` frees the
    phone for a fresh signup (the unique constraint only covers non-empty hashes).

    Offboarding orchestration (Codex #13), all inside this one transaction so it
    commits atomically with the anonymisation:

    1. **Fan memberships** — every ACTIVE subscription this account holds as a fan is
       terminated immediately (``status=cancelled`` + ``cancelled_at``, #5 lifecycle).
       No charge is taken: ``cancelled`` rows leave the billing worker's ACTIVE-only
       candidate set, so the mock renewal never re-bills a gone member.
    2. **Creator storefront** — if this account operates a creator profile, the
       profile is unpublished (hidden from the public list/detail/search reads),
       every product is set ``hidden`` (owner-only — excluded by
       :func:`apps.commerce.api._public_product_qs`, so it can no longer be seen or
       ordered), and every tier is deactivated (the subscribe path only accepts
       ``active`` tiers), so nothing of theirs stays publicly purchasable. Nothing is
       deleted — the storefront rows are kept for history under the pseudonymous id.
    3. **Comment snapshots** — the display ``author_name`` denormalised onto this
       account's comments is blanked, consistent with the account anonymisation (the
       ``author`` FK is kept for linkage).

    Append-only/legal-hold safe: orders, settlements, reversals, and events keep
    their ``fan_id`` FK (now pseudonymous); no financial/audit row is deleted here —
    the gated retention sweep owns the final PII hard-purge.

    Idempotent: re-withdrawing an already-withdrawn account is a no-op (the
    ``withdrawn_at`` early return short-circuits the whole orchestration). Per-channel
    marketing consent is cleared here (D8).
    """
    if account.withdrawn_at is not None:
        return
    # Lazy imports: these apps' models/services import identity.models, so importing
    # them at module load would risk an import cycle. Resolved per call.
    from apps.commerce.models import Product, ProductStatus
    from apps.consent.services import clear_marketing_consent
    from apps.content.models import Comment
    from apps.creator.models import Creator
    from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus

    now = timezone.now()

    # 1) Terminate the fan's own active subscriptions immediately (no charge).
    Subscription.objects.filter(
        fan=account, status=SubscriptionStatus.ACTIVE.value
    ).update(status=SubscriptionStatus.CANCELLED.value, cancelled_at=now)

    # 2) Unpublish the creator storefront (profile + products + tiers) if any.
    creator = Creator.objects.filter(owner=account).first()
    if creator is not None:
        if creator.published:
            creator.published = False
            creator.save(update_fields=["published"])
        Product.objects.filter(creator=creator).exclude(
            status=ProductStatus.HIDDEN.value
        ).update(status=ProductStatus.HIDDEN.value)
        MembershipTier.objects.filter(creator=creator, active=True).update(active=False)

    # 3) Pseudonymise the display-name snapshot on this account's comments.
    Comment.objects.filter(author=account).exclude(author_name="").update(author_name="")

    revoke_all_for_account(account, reason="withdrawal")
    clear_marketing_consent(account)
    account.nickname = ""
    account.auth_subject_hash = ""
    account.is_active = False
    account.withdrawn_at = now
    account.save(
        update_fields=["nickname", "auth_subject_hash", "is_active", "withdrawn_at"]
    )


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
