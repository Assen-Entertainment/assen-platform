"""Feature flags: a keyed on/off switch with safe defaults.

P0 is Fan CRM; the P1/P2 monetization features (fanletter, digital cheki,
membership, paid messages) ship behind flags that start *off* and must not
precede safety/report/block (CONSTRAINTS Company-OS inheritance). The flag *keys*
and their default state are declared as code constants in
:mod:`apps.feature_flag.seeds` and synced into rows by a function (not a data
migration), so seeding does not touch the migrations human-gate (#25).
"""

from __future__ import annotations

import re
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

# Keys are snake_case identifiers (Django-safe); the dotted Tech-Arch notation
# (``p1.fanletter_beta``) is not a valid identifier, so snake_case is canonical
# (P0_Scope_Reconciliation L66).
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_flag_key(value: str) -> None:
    """Reject non-snake_case flag keys at the model boundary.

    Enforcing the shape here means a typo'd or dotted key cannot be persisted and
    later silently miss every ``is_enabled`` lookup.
    """
    if not _KEY_RE.match(value):
        raise ValidationError(
            f"Feature flag key '{value}' must be snake_case "
            "(lowercase, digits, underscores; starting with a letter)."
        )


class FeatureFlag(models.Model):
    """One named feature toggle, defaulting to disabled.

    ``enabled`` defaults to False so a newly introduced flag is dark until
    explicitly turned on — the safe direction for monetization gates.
    """

    key = models.CharField(
        max_length=64, unique=True, validators=[validate_flag_key]
    )
    enabled = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Validate the key on every save so invalid keys never persist."""
        validate_flag_key(self.key)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Show the flag key and its current state."""
        return f"flag:{self.key}={'on' if self.enabled else 'off'}"
