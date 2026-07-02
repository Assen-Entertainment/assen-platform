"""Canonical P1/P2 feature-flag seed definitions (code constants, not data migration).

Source: Company-OS P0_Scope_Reconciliation feature-flag table (11 flags). These
are declared in code and reconciled into rows by
:func:`apps.feature_flag.services.sync_flags`, deliberately avoiding a data
migration so flag seeding stays clear of the migrations human-gate (#25). Every
seed starts ``enabled=False``: monetization and future features are dark until
explicitly enabled, and never before safety/report/block.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FlagSeed:
    """A declared flag and the state it should be seeded with.

    ``enabled`` is always False at P0; it is a field (not a constant True/False)
    so the seed list is self-documenting and a future flag could, in principle,
    ship on without changing the sync code.
    """

    key: str
    enabled: bool
    description: str


# The 11 reconciled flags. Keys are snake_case (dotted Tech-Arch notation is not a
# valid Django identifier). ``future_*`` flags are permanently off at P0/P1.
FLAG_SEEDS: tuple[FlagSeed, ...] = (
    FlagSeed("p1_fanletter_beta", False, "P1 fanletter beta (Gate 4 + safety policy)."),
    FlagSeed("p1_digital_cheki_beta", False, "P1 digital cheki beta (safety policy)."),
    FlagSeed("p1_postal_cheki_beta", False, "P1 postal cheki beta (shipping PII split)."),
    FlagSeed("p1_remote_gift_beta", False, "P1 remote gift beta (remote gift policy)."),
    FlagSeed("p2_membership_beta", False, "P2 membership (subscription compliance)."),
    FlagSeed("p2_paid_content_beta", False, "P2 paid content (P2 prerequisite)."),
    FlagSeed("p2_cast_message_beta", False, "P2 cast broadcast message (moderated)."),
    FlagSeed("pos_api_sync", False, "POS API sync (4-week manual stability gate)."),
    FlagSeed("future_dm", False, "Direct messaging — permanently off at P0/P1."),
    FlagSeed("future_video_call", False, "Video call — permanently off at P0/P1."),
    FlagSeed("future_fan_ranking", False, "Fan ranking — permanently off at P0/P1."),
)
