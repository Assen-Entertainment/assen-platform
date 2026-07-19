"""Backfill creator content categories onto existing (blank-category) creators.

Before category could be set through the product (there was no UI/API path to set
``Creator.category``), every existing creator — including the deployed E2E seed
creator ``@e2ecreator`` — was left with ``category=""``, so the discovery category
filter (exact match) matched nothing. This command assigns a canonical category
(:data:`~apps.creator.categories.CREATOR_CATEGORIES`) to known demo/seed creators.

Idempotent and non-destructive: it only fills a **blank** category, never
overwrites one already set (a creator who chose their own category is left alone),
and it creates no rows / touches no PII. Safe to re-run.

    python manage.py backfill_creator_categories
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.creator.categories import CREATOR_CATEGORIES
from apps.creator.models import Creator

# Known demo/seed handles → canonical category. The deployed E2E seed creator
# (@e2ecreator) is included so the live discovery filter demonstrates immediately;
# the rest mirror seed_demo so a partially-seeded DB converges to the same mapping.
_HANDLE_CATEGORIES: dict[str, str] = {
    "e2ecreator": "버튜버",
    "stellar": "일러스트",
    "neonbeats": "뮤직",
    "rabbit": "버튜버",
    "myo": "일러스트",
    "lumi": "일러스트",
}

# Fallback for any other blank-category creator, so the filter is never empty for a
# populated surface. Kept canonical (first entry) — deliberately generic.
_DEFAULT_CATEGORY = CREATOR_CATEGORIES[0]


class Command(BaseCommand):
    """Assign canonical categories to creators that still have a blank category."""

    help = "Backfill Creator.category for blank-category creators (idempotent)."

    def add_arguments(self, parser: Any) -> None:
        """`--default-all` also fills unknown blank creators with the fallback."""
        parser.add_argument(
            "--default-all",
            action="store_true",
            help=(
                "Also assign the fallback category to any other creator whose "
                "category is still blank (not just the known demo handles)."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Fill blank categories from the known mapping (and optionally a fallback)."""
        del args
        updated = 0
        for creator in Creator.objects.filter(category=""):
            mapped = _HANDLE_CATEGORIES.get(creator.handle)
            if mapped is None:
                if not options.get("default_all"):
                    continue
                mapped = _DEFAULT_CATEGORY
            creator.category = mapped
            creator.save(update_fields=["category"])
            updated += 1
            self.stdout.write(f"  @{creator.handle} → {mapped}")
        self.stdout.write(
            self.style.SUCCESS(f"backfilled category on {updated} creator(s).")
        )
