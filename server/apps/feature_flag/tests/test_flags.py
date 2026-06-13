"""Acceptance tests for feature-flag evaluation and seed sync.

Covers: default-off behaviour, snake_case key validation, the 11 reconciled
seeds, idempotent sync that preserves operator toggles, and unknown-key
fail-closed evaluation.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.feature_flag.models import FeatureFlag
from apps.feature_flag.seeds import FLAG_SEEDS
from apps.feature_flag.services import is_enabled, sync_flags

pytestmark = pytest.mark.django_db


def test_unknown_flag_is_disabled() -> None:
    """An undeclared/absent flag evaluates to off (fail closed)."""
    assert is_enabled("nonexistent_flag") is False


def test_flag_defaults_off() -> None:
    """A created flag is off unless explicitly enabled."""
    FeatureFlag.objects.create(key="some_flag")
    assert is_enabled("some_flag") is False
    FeatureFlag.objects.filter(key="some_flag").update(enabled=True)
    assert is_enabled("some_flag") is True


def test_non_snake_case_key_rejected() -> None:
    """A dotted/invalid key cannot be saved."""
    with pytest.raises(ValidationError):
        FeatureFlag(key="p1.fanletter_beta").save()


def test_sync_creates_eleven_seeds_all_off() -> None:
    """Syncing creates the 11 reconciled flags, every one disabled."""
    result = sync_flags()
    assert len(result.created) == 11
    assert FeatureFlag.objects.count() == 11
    # Every seeded flag starts off (monetization/future stays dark at P0).
    assert FeatureFlag.objects.filter(enabled=True).count() == 0
    # Spot-check a representative key from each tier.
    for key in ("p1_fanletter_beta", "p2_membership_beta", "future_dm"):
        assert FeatureFlag.objects.filter(key=key).exists()


def test_sync_is_idempotent_and_preserves_runtime_toggle() -> None:
    """Re-sync creates nothing new and does not reset an operator's enable."""
    sync_flags()
    # An operator turns one flag on at runtime.
    FeatureFlag.objects.filter(key="p1_fanletter_beta").update(enabled=True)

    result = sync_flags()
    assert result.created == ()
    assert len(result.existing) == 11
    # The manual enable survives the re-sync.
    assert is_enabled("p1_fanletter_beta") is True


def test_all_seed_keys_are_snake_case() -> None:
    """Every declared seed key is a valid snake_case identifier."""
    for seed in FLAG_SEEDS:
        # Saving validates the key; a bad seed would raise here.
        FeatureFlag(key=seed.key, enabled=seed.enabled).save()
    assert FeatureFlag.objects.count() == len(FLAG_SEEDS)
