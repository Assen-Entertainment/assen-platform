"""Identity and opaque-token models (staged identity, ADR-0002).

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26). This module defines the token
store backing authentication; changes here are gated on human review.

Design (ADR-0002): access tokens are opaque, server-stored, and short-lived so
they can be revoked instantly (safety F11). Refresh tokens rotate — each use
mints a new one and supersedes the old — and a whole token *family* is revoked
if a superseded refresh token is replayed (reuse detection). Only the SHA-256
hash of a token is ever stored; the plaintext is returned to the caller exactly
once at issuance and is unrecoverable afterward.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from django.db import models
from django.utils import timezone


class Role(models.TextChoices):
    """The six platform roles (ASS-91, Technical Architecture role matrix).

    ``fan``/``cast`` are end users; ``operator``/``manager``/``admin`` are staff
    with widening privilege; ``system`` is for jobs/imports/webhooks. RBAC route
    and field guards key off this value.
    """

    FAN = "fan", "fan"
    CAST = "cast", "cast"
    OPERATOR = "operator", "operator"
    MANAGER = "manager", "manager"
    ADMIN = "admin", "admin"
    SYSTEM = "system", "system"


class AnonymousSession(models.Model):
    """A pre-signup identity used to record activity before a fan account exists.

    Staged identity: QR/web entry creates an ``anonymous_id`` so visits can be
    logged immediately; on signup it is merged into an :class:`Account` and the
    prior events are linked (not rewritten) so MSFC is not double-counted
    (Data_Event_Schema L764-769).
    """

    anonymous_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Set once the anonymous identity has been merged into a fan account.
    merged_into = models.ForeignKey(
        "identity.Account",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="merged_anonymous_sessions",
    )

    def __str__(self) -> str:
        """Identify the session by its anonymous id."""
        return f"anon:{self.anonymous_id}"


class Account(models.Model):
    """An authenticated principal (fan, cast, or staff member).

    ``fan_id`` is the stable external identifier used across the event log and
    domain apps. ``role`` drives RBAC. Operator/staff accounts are flagged so fan
    metrics (MSFC) can exclude them per ASS-90/#1.
    """

    fan_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.FAN)
    # Username + password hash are only populated for staff/operator logins
    # (ASS-91). Fans authenticate via the staged-identity / social flow (ADR-0002,
    # provider TBD) and leave these blank.
    username = models.CharField(max_length=150, blank=True, default="", db_index=True)
    password_hash = models.CharField(max_length=256, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_operator_account(self) -> bool:
        """True for staff roles excluded from fan metrics (MSFC, #1).

        Operator/manager/admin/system activity must not inflate fan KPIs, so this
        flag is the single predicate metric queries consult.
        """
        return self.role in {
            Role.OPERATOR.value,
            Role.MANAGER.value,
            Role.ADMIN.value,
            Role.SYSTEM.value,
        }

    def __str__(self) -> str:
        """Identify the account by role and fan id."""
        return f"{self.role}:{self.fan_id}"


class TokenFamily(models.Model):
    """A refresh-token lineage created at login and revoked as a unit on reuse.

    Rotation chains refresh tokens within one family. Detecting replay of a
    superseded token revokes the entire family (``revoked=True``), forcing
    re-authentication — the standard refresh-reuse defense (ADR-0002).
    """

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="token_families"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=64, blank=True, default="")

    def revoke(self, *, reason: str) -> None:
        """Revoke the whole family, recording when and why."""
        self.revoked = True
        self.revoked_at = timezone.now()
        self.revoked_reason = reason
        self.save(update_fields=["revoked", "revoked_at", "revoked_reason"])

    def __str__(self) -> str:
        """Identify the family and its state."""
        state = "revoked" if self.revoked else "active"
        return f"family:{self.pk}:{state}"


class AccessToken(models.Model):
    """A short-lived opaque access token, stored only as a SHA-256 hash.

    Lookup is by hash so the plaintext never persists. ``revoked`` plus
    ``expires_at`` make validity a server-side decision, enabling instant
    revocation (F11). The plaintext is shown to the client once at issuance.
    """

    family = models.ForeignKey(
        TokenFamily, on_delete=models.CASCADE, related_name="access_tokens"
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)

    def is_valid(self, *, now: datetime | None = None) -> bool:
        """True if the token is neither revoked nor expired.

        Centralises the validity rule so the auth class and tests agree on what
        "usable" means.
        """
        moment = timezone.now() if now is None else now
        return (not self.revoked) and self.expires_at > moment

    def __str__(self) -> str:
        """Identify by family without exposing the secret."""
        return f"access:family={self.family_id}"


class RefreshToken(models.Model):
    """A rotating refresh token, stored only as a SHA-256 hash.

    Each refresh consumes the current token (``used=True``) and issues a
    successor. Presenting an already-used token is replay: the family is revoked.
    """

    family = models.ForeignKey(
        TokenFamily, on_delete=models.CASCADE, related_name="refresh_tokens"
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    # Set when this token is rotated; presenting a used token is treated as reuse.
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self, *, now: datetime | None = None) -> bool:
        """True if the refresh token is unused, unexpired, and family is active."""
        moment = timezone.now() if now is None else now
        return (not self.used) and self.expires_at > moment and not self.family.revoked

    def mark_used(self) -> None:
        """Mark this refresh token consumed by a successful rotation."""
        self.used = True
        self.used_at = timezone.now()
        self.save(update_fields=["used", "used_at"])

    def __str__(self) -> str:
        """Identify by family without exposing the secret."""
        return f"refresh:family={self.family_id}:used={self.used}"
