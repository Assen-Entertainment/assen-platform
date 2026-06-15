"""Seed a deterministic POS-link scenario for the E2E gate (ASS-102 v0).

Run against a throwaway sqlite DB via the Django shell::

    POS_SEED_OUT=/abs/path/.pos_seed.json \
      uv run python manage.py shell < ../e2e/seed_pos.py

Creates operator/fan accounts + tokens, records two visits on an **isolated seed
date** (so coverage totals are deterministic regardless of other suites' data),
and manually links one of them to a POS receipt. Writes the tokens + the expected
coverage to ``$POS_SEED_OUT`` for the Playwright spec to assert against. The
fan_id lets the spec create a fresh visit via the API for the link round-trip.
Dev/E2E only.
"""

import json
import os
from datetime import datetime

from django.utils import timezone

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.pos_lite.services import link_pos_order
from apps.visit.services import record_visit

out_path = os.environ["POS_SEED_OUT"]

operator = Account.objects.create(role=Role.OPERATOR.value)
fan = Account.objects.create(role=Role.FAN.value)
operator_token = issue_token_pair(operator).access_token
fan_token = issue_token_pair(fan).access_token

# An isolated past date so the coverage totals below are not perturbed by visits
# other suites seed on "today".
seed_at = timezone.make_aware(datetime(2026, 3, 2, 12, 0))
seed_date = "2026-03-02"

linked_visit = record_visit(fan=fan, visited_at=seed_at, actor=operator)
unlinked_visit = record_visit(fan=fan, visited_at=seed_at, actor=operator)

link_pos_order(
    visit=linked_visit,
    actor=operator,
    pos_receipt_no="POS-SEED-1",
    payment_status="paid",
    payment_method="card",
    amount=15000,
)

payload = {
    "operatorToken": operator_token,
    "fanToken": fan_token,
    "fanId": str(fan.fan_id),
    "seedDate": seed_date,
    "linkedReceipt": "POS-SEED-1",
    "unlinkedVisitId": str(unlinked_visit.id),
    "expected": {
        "total_active_visits": 2,
        "linked_visits": 1,
        "unlinked_visits": 1,
        "link_rate": 0.5,
    },
}
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
print(f"SEEDED -> {out_path}")
