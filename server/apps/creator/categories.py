"""Canonical creator content categories — the single source of truth (server side).

A :class:`~apps.creator.models.Creator` optionally identifies with ONE content
category, used by discovery filtering (``GET /creators?category=…``) and shown as
the creator's meta. This tuple is the closed set the profile-edit / become-creator
endpoints validate against (empty string ``""`` = "unset" is always allowed).

These are **content-creation** categories. 굿즈 (goods) is deliberately excluded —
it is a *product type* (see the store product filters), not a creator category.

Kept in lockstep with the web mirror ``web/src/lib/creator-categories.ts``; the
two lists MUST stay identical (same values, same order). Change both together.
"""

from __future__ import annotations

# Order is the canonical display order the web filter/selector renders.
CREATOR_CATEGORIES: tuple[str, ...] = (
    "일러스트",
    "뮤직",
    "버튜버",
    "게임",
    "사진",
    "코스프레",
    "글",
)


def is_valid_category(value: str) -> bool:
    """Whether ``value`` is a settable creator category (canonical, or "" to clear)."""
    return value == "" or value in CREATOR_CATEGORIES
