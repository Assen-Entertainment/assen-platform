"""``purge_expired_data`` — run the data-retention sweep (D2/D6, Codex #19).

Privacy decisions 2026-07-12 (legal-minimum retention). Shares one code path with the
nightly Celery task (apps.identity.tasks.run_retention_sweep) via the registry in
:mod:`apps.identity.retention`. FAIL-CLOSED: the sweep only deletes/blanks rows when
``settings.RETENTION_PURGE_ENABLED`` is True; with it off (default) the command reports
what would be purged and changes nothing. ``--dry-run`` forces report-only even when the
master switch is on (e.g. to preview before enabling).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
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
            help="Report what would be purged without deleting (forces report-only).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Run the sweep and print per-class matched counts + the effective mode."""
        dry_run = bool(options["dry_run"])
        result = run_retention_sweep(dry_run=dry_run)
        executing = settings.RETENTION_PURGE_ENABLED and not dry_run
        mode = "purge executed" if executing else "dry-run only (nothing deleted)"
        self.stdout.write(f"retention sweep [{mode}]:")
        for category, count in result.items():
            self.stdout.write(f"  {category}: {count} row(s) past retention window")
