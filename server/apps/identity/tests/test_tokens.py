"""Acceptance tests for opaque-token issuance, rotation, revocation, reuse.

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26) — exercises the auth surface.

Covers ADR-0002 acceptance criteria: issue, verify, rotate (with a fresh pair),
instant revocation, refresh-reuse detection collapsing the whole family, and the
sha256-only storage guarantee.
"""

from __future__ import annotations

import pytest

from apps.identity.models import (
    AccessToken,
    Account,
    RefreshToken,
    Role,
    TokenFamily,
)
from apps.identity.services import (
    TokenError,
    authenticate_operator,
    hash_token,
    issue_token_pair,
    revoke_family,
    rotate_refresh_token,
    verify_access_token,
)

pytestmark = pytest.mark.django_db


def _fan() -> Account:
    """Create a basic fan account."""
    return Account.objects.create(role=Role.FAN.value)


def test_issue_returns_plaintext_but_stores_only_hash() -> None:
    """Issued plaintext is usable, yet only its hash is persisted."""
    account = _fan()
    pair = issue_token_pair(account)

    stored = AccessToken.objects.get()
    assert stored.token_hash == hash_token(pair.access_token)
    # The plaintext itself appears nowhere in the row.
    assert pair.access_token != stored.token_hash
    refresh_stored = RefreshToken.objects.get()
    assert refresh_stored.token_hash == hash_token(pair.refresh_token)


def test_verify_access_token_resolves_account() -> None:
    """A freshly issued access token verifies back to its account."""
    account = _fan()
    pair = issue_token_pair(account)
    resolved = verify_access_token(pair.access_token)
    assert resolved.pk == account.pk


def test_verify_unknown_token_raises() -> None:
    """An unrecognised token is rejected."""
    with pytest.raises(TokenError):
        verify_access_token("definitely-not-a-real-token")


def test_rotation_issues_new_pair_and_consumes_old_refresh() -> None:
    """Rotating returns a new pair and the old refresh becomes invalid."""
    account = _fan()
    pair = issue_token_pair(account)

    rotated = rotate_refresh_token(pair.refresh_token)
    assert rotated.access_token != pair.access_token
    assert rotated.refresh_token != pair.refresh_token

    # New access token works.
    assert verify_access_token(rotated.access_token).pk == account.pk
    # Old refresh is now used; presenting it again is reuse (see next test).
    old = RefreshToken.objects.get(token_hash=hash_token(pair.refresh_token))
    assert old.used is True


def test_refresh_reuse_detection_revokes_family() -> None:
    """Replaying a consumed refresh token revokes the whole family."""
    account = _fan()
    pair = issue_token_pair(account)

    # Legitimate rotation consumes the original refresh token.
    rotated = rotate_refresh_token(pair.refresh_token)

    # Attacker replays the original (now-used) refresh token.
    with pytest.raises(TokenError):
        rotate_refresh_token(pair.refresh_token)

    family = TokenFamily.objects.get()
    assert family.revoked is True
    assert family.revoked_reason == "refresh_reuse_detected"

    # Every token in the family is now dead, including the honest client's
    # most-recent access + refresh.
    with pytest.raises(TokenError):
        verify_access_token(rotated.access_token)
    with pytest.raises(TokenError):
        rotate_refresh_token(rotated.refresh_token)


def test_revoke_family_invalidates_access_immediately() -> None:
    """Revoking a family makes its access token fail verification at once (F11)."""
    account = _fan()
    pair = issue_token_pair(account)
    family = TokenFamily.objects.get()

    revoke_family(family, reason="logout")

    with pytest.raises(TokenError):
        verify_access_token(pair.access_token)


def test_operator_login_with_correct_password() -> None:
    """An operator authenticates with the right password and is rejected on wrong."""
    from django.contrib.auth.hashers import make_password

    operator = Account.objects.create(
        role=Role.OPERATOR.value,
        username="op_alice",
        password_hash=make_password("correct horse"),
    )
    authed = authenticate_operator(username="op_alice", password="correct horse")
    assert authed.pk == operator.pk

    with pytest.raises(TokenError):
        authenticate_operator(username="op_alice", password="wrong")


def test_fan_cannot_use_operator_login() -> None:
    """A fan row (no password / fan role) cannot authenticate as an operator."""
    Account.objects.create(role=Role.FAN.value, username="not_staff")
    with pytest.raises(TokenError):
        authenticate_operator(username="not_staff", password="anything")
