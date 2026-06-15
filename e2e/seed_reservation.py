"""Seed a deterministic reservation scenario for the E2E gate (ASS-109 v0).

Run against a throwaway sqlite DB via the Django shell::

    RESERVATION_SEED_OUT=/abs/path/.reservation_seed.json \
      uv run python manage.py shell < ../e2e/seed_reservation.py

Creates operator/fan accounts + tokens, a separately-blocked fan (active
``reservation`` block — the ASS-111 enforcement target), and two reservations
for the fan on a **future, isolated date** (so the daily-list totals are
deterministic and pass the past-date guard whenever the gate runs). Writes the
tokens + the seed date to ``$RESERVATION_SEED_OUT`` for the Playwright spec.
Dev/E2E only.
"""

import json
import os
from datetime import time, timedelta

from django.utils import timezone

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.reservation.services import confirm_reservation, create_reservation
from apps.safety.models import BlockScope, UserBlock

out_path = os.environ["RESERVATION_SEED_OUT"]

operator = Account.objects.create(role=Role.OPERATOR.value)
fan = Account.objects.create(role=Role.FAN.value)
blocked_fan = Account.objects.create(role=Role.FAN.value)

operator_token = issue_token_pair(operator).access_token
fan_token = issue_token_pair(fan).access_token
blocked_fan_token = issue_token_pair(blocked_fan).access_token

# Hard block on the reservation surface — the enforcement ASS-111 deferred to F03.
UserBlock.objects.create(
    target=blocked_fan,
    block_scope=BlockScope.RESERVATION.value,
    block_reason="policy_violation",
    effective_from=timezone.now(),
    created_by=operator,
)

# A future, isolated date: passes the past-date guard and is far from any "today"
# rows other suites seed, so the daily-list count is deterministic.
seed_date = timezone.localdate() + timedelta(days=180)

create_reservation(
    fan=fan, actor=operator, reserved_date=seed_date, reserved_time=time(13, 0), party_size=2
)
confirmed = create_reservation(
    fan=fan, actor=operator, reserved_date=seed_date, reserved_time=time(15, 0), party_size=3
)
confirm_reservation(reservation=confirmed, actor=operator)

payload = {
    "operatorToken": operator_token,
    "fanToken": fan_token,
    "blockedFanToken": blocked_fan_token,
    "fanId": str(fan.fan_id),
    "seedDate": seed_date.isoformat(),
    "expected": {"total": 2},
}
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
print(f"SEEDED -> {out_path}")
