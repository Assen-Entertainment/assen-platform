"""Acceptance tests for opaque-token issuance, rotation, revocation, reuse.

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26) — exercises the auth surface.

Covers ADR-0002 acceptance criteria: issue, verify, rotate (with a fresh pair),
instant revocation, refresh-reuse detection collapsing the whole family, and the
sha256-only storage guarantee.
"""

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest
from django.db.models.query import QuerySet

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


def test_concurrent_rotation_second_consume_fails_and_burns_family() -> None:
    """A rotation that loses the atomic consume race is treated as reuse (A1).

    Simulates two rotations racing on the same refresh token: both pass the
    ``used``/revoked pre-check on their snapshot, but only one conditional UPDATE
    (``WHERE used = FALSE``) can match. Force the *losing* side by making the
    refresh-consume UPDATE report 0 rows — the rotation must then burn the family
    and raise, never mint a second successor pair.
    """
    account = _fan()
    pair = issue_token_pair(account)

    real_update = QuerySet.update

    def sabotage_refresh_consume(self: QuerySet[Any], *args: object, **kwargs: object) -> int:
        # Only the refresh-token consume (used=True) loses the race; every other
        # UPDATE (e.g. revoke_family's access-token flip) runs for real.
        if self.model is RefreshToken and kwargs.get("used") is True:
            return 0
        return real_update(self, *args, **kwargs)

    with mock.patch.object(QuerySet, "update", sabotage_refresh_consume):
        with pytest.raises(TokenError):
            rotate_refresh_token(pair.refresh_token)

    # No successor pair was minted, and the family is burned as reuse.
    family = TokenFamily.objects.get()
    assert family.revoked is True
    assert family.revoked_reason == "refresh_reuse_detected"
    # Only the original access + refresh exist (no second successor pair leaked).
    assert AccessToken.objects.count() == 1
    assert RefreshToken.objects.count() == 1
    # The burned family's original access token no longer verifies.
    with pytest.raises(TokenError):
        verify_access_token(pair.access_token)


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


def test_duplicate_staff_username_is_rejected_by_constraint() -> None:
    """A second account with the same non-empty username violates the partial unique.

    ``authenticate_operator`` resolves the login with ``.get(username=…)``; the
    ``uniq_staff_username`` partial constraint keeps that lookup single-valued so it
    can never raise MultipleObjectsReturned (→ 500) on a collided username.
    """
    from django.db import IntegrityError, transaction

    Account.objects.create(role=Role.OPERATOR.value, username="op_dup")
    with pytest.raises(IntegrityError), transaction.atomic():
        Account.objects.create(role=Role.MANAGER.value, username="op_dup")


def test_blank_username_is_not_constrained() -> None:
    """Many accounts may keep the default empty username (fans/non-login staff).

    The unique is partial (``username != ''``), so the common case of blank
    usernames is unconstrained — otherwise every fan row (all "") would collide.
    """
    for _ in range(3):
        Account.objects.create(role=Role.FAN.value)  # username defaults to ""
    assert Account.objects.filter(username="").count() == 3


@pytest.mark.django_db
def test_access_token_rejected_when_family_revoked_even_if_row_not_flagged() -> None:
    """Family-level gate: 소각-회전 경합으로 access 행이 revoked=False로 남아도 거부된다."""
    account = Account.objects.create(role=Role.FAN.value, nickname="레이스팬")
    pair = issue_token_pair(account)
    # 경합 시뮬레이션: revoke_family()의 벌크 access 플립 없이 family만 소각.
    family = TokenFamily.objects.filter(account=account).latest("created_at")
    family.revoke(reason="race-simulation")
    assert AccessToken.objects.filter(family=family, revoked=False).exists()

    with pytest.raises(TokenError):
        verify_access_token(pair.access_token)
