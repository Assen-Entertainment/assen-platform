"""``purge_expired_data`` — run the data-retention sweep (D2/D6).

Privacy decisions 2026-07-12 (legal-minimum retention). Intended to run nightly in
production (scheduled task / cron). Use ``--dry-run`` to report what would be purged
without deleting. The actual purge logic lives in :mod:`apps.identity.retention` so
it is unit-testable independently of the command.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.identity.retention import run_retention_sweep


class Command(BaseCommand):
    """Purge data past its retention window (see apps.identity.retention)."""

    help = "Purge data past its retention window (D2/D6, privacy decisions 2026-07-12)."

    def add_arguments(self, parser: Any) -> None:
        """Register the ``--dry-run`` flag (report counts without deleting)."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be purged without deleting anything.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Run the sweep and print per-category counts."""
        dry_run = bool(options["dry_run"])
        result = run_retention_sweep(dry_run=dry_run)
        verb = "would purge" if dry_run else "purged"
        for category, count in result.items():
            self.stdout.write(f"{category}: {verb} {count}")
