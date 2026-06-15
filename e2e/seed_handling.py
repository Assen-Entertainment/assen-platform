"""Seed a deterministic report-handling scenario for the E2E gate (ASS-111).

Run against a throwaway sqlite DB via the Django shell::

    HANDLING_SEED_OUT=/abs/path/.handling_seed.json \
      uv run python manage.py shell < ../e2e/seed_handling.py

Creates operator/manager/fan accounts + tokens, files reports in three open
states (received/reviewing/actioned at distinct severities) and resolves one,
then writes the tokens + expected aggregate values to ``$HANDLING_SEED_OUT`` for
the Playwright spec to assert against (values derived from the seeded rows,
independent of the code under test). Dev/E2E only.
"""

import json
import os

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.safety.models import ReportStatus
from apps.safety.services import change_report_status, file_report, resolve_report

out_path = os.environ["HANDLING_SEED_OUT"]

operator = Account.objects.create(role=Role.OPERATOR.value)
manager = Account.objects.create(role=Role.MANAGER.value)
fan = Account.objects.create(role=Role.FAN.value)
operator_token = issue_token_pair(operator).access_token
fan_token = issue_token_pair(fan).access_token


def _file(severity):
    return file_report(
        report_type="other",
        severity=severity,
        reporter_type="fan",
        target_type="fan",
        narrative="seed narrative (restricted)",
        actor=operator,
    )


# Three open reports at distinct statuses + severities.
_file("low")  # received / low
reviewing = _file("high")
change_report_status(report=reviewing, status=ReportStatus.REVIEWING.value, actor=operator)
actioned = _file("critical")
change_report_status(report=actioned, status=ReportStatus.ACTIONED.value, actor=operator)

# One resolved report (medium): leaves the open queue, counts toward throughput
# within the default 30-day window.
done = _file("medium")
resolve_report(report=done, resolution="actioned_other", resolution_note="처리됨", actor=manager)

payload = {
    "operatorToken": operator_token,
    "fanToken": fan_token,
    "expected": {
        "open_total": 3,
        "open_received": 1,
        "open_reviewing": 1,
        "open_actioned": 1,
        "open_low": 1,
        "open_medium": 0,
        "open_high": 1,
        "open_critical": 1,
        "resolved_in_window": 1,
    },
}
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
print(f"SEEDED -> {out_path}")
