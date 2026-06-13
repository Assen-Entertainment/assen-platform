"""Feature-flag evaluation and seed synchronisation.

``is_enabled`` is the single read path domain code uses to gate a feature.
``sync_flags`` reconciles the declared :data:`FLAG_SEEDS` into ``FeatureFlag``
rows without a data migration: it creates missing flags at their declared default
and never clobbers an operator's runtime toggle of an existing flag.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.feature_flag.models import FeatureFlag
from apps.feature_flag.seeds import FLAG_SEEDS


@dataclass(frozen=True)
class SyncResult:
    """What :func:`sync_flags` changed, for logging and tests."""

    created: tuple[str, ...]
    existing: tuple[str, ...]


def is_enabled(key: str) -> bool:
    """Return whether the flag ``key`` is on; unknown keys are treated as off.

    Defaulting unknown/absent flags to off keeps a missing seed or typo from
    accidentally exposing a gated feature — failure closes the gate.
    """
    return FeatureFlag.objects.filter(key=key, enabled=True).exists()


def sync_flags() -> SyncResult:
    """Ensure every declared seed exists as a row, returning what changed.

    Idempotent: existing flags are left exactly as they are (so a manual enable
    in ops is preserved), and only missing flags are created at their declared
    default. This is the migration-free seeding entry point — call it from app
    startup or a management command, never from a data migration (#25).
    """
    created: list[str] = []
    existing: list[str] = []
    for seed in FLAG_SEEDS:
        _, was_created = FeatureFlag.objects.get_or_create(
            key=seed.key,
            defaults={"enabled": seed.enabled, "description": seed.description},
        )
        (created if was_created else existing).append(seed.key)
    return SyncResult(created=tuple(created), existing=tuple(existing))
