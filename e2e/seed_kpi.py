"""Seed a deterministic KPI scenario into a live dev DB for the E2E gate.

Run inside the server's Django shell against a throwaway sqlite DB, e.g.::

    KPI_SEED_OUT=/abs/path/.seed.json \
      uv run python manage.py shell < ../e2e/seed_kpi.py

It creates an operator + a fan account, issues access tokens, emits a small,
known event set (one MSFC-qualifying fan, one start-only fan, one safety report,
one block), and writes the tokens + window + expected metric values to
``$KPI_SEED_OUT`` for the Playwright spec to assert against. Dev/E2E only.
"""

import json
import os
from datetime import timedelta

from django.utils import timezone

from apps.dashboard.metrics import month_bounds
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import emit_event
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.safety.models import BlockScope, BlockStatus, UserBlock

out_path = os.environ["KPI_SEED_OUT"]
now = timezone.now()

operator = Account.objects.create(role=Role.OPERATOR.value)
fan = Account.objects.create(role=Role.FAN.value)
operator_token = issue_token_pair(operator).access_token
fan_token = issue_token_pair(fan).access_token


def _visit(fan_id, when, visit_id):
    emit_event(
        event_name=EventName.VISIT_CHECKED_IN.value,
        occurred_at=when,
        actor_type=ActorType.FAN.value,
        source=EventSource.KIOSK.value,
        fan_id=fan_id,
        visit_id=visit_id,
        payload={
            "visit_id": visit_id,
            "store_id": "store-1",
            "business_day": when.date().isoformat(),
            "visit_type": "store_visit",
            "checkin_method": "qr",
            "is_verified_offline_visit": True,
        },
    )


# Fan with a safe follow-up within 30 days -> MSFC qualifies.
_visit("e2e-msfc", now, "e2e-v1")
emit_event(
    event_name=EventName.FAVORITE_ADDED.value,
    occurred_at=now + timedelta(days=5),
    actor_type=ActorType.FAN.value,
    source=EventSource.FAN_APP.value,
    fan_id="e2e-msfc",
    payload={"fan_id": "e2e-msfc", "cast_id": "cast-1", "favorite_source": "profile"},
)
# Fan with a verified visit but no follow-up -> start only, not MSFC.
_visit("e2e-start", now, "e2e-v2")

# Guardrail events.
emit_event(
    event_name=EventName.SAFETY_REPORT_CREATED.value,
    occurred_at=now,
    actor_type=ActorType.OPERATOR.value,
    source=EventSource.MANUAL.value,
    actor_is_operator=True,
    payload={
        "safety_report_id": "e2e-r1",
        "reporter_type": "cast",
        "target_type": "fan",
        "report_type": "unwanted_request",
        "severity": "low",
        "visibility": "restricted",
    },
)
emit_event(
    event_name=EventName.USER_BLOCKED.value,
    occurred_at=now,
    actor_type=ActorType.OPERATOR.value,
    source=EventSource.MANUAL.value,
    actor_is_operator=True,
    payload={
        "block_id": "e2e-b1",
        "block_scope": "all",
        "block_reason": "policy_violation",
        "effective_from": now.isoformat(),
    },
)

# A blocked fan exercises the safety-model join end-to-end: a verified visit +
# favorite that WOULD qualify for MSFC, but the active block excludes the fan.
blocked = Account.objects.create(role=Role.FAN.value)
_visit(str(blocked.fan_id), now, "e2e-v3")
emit_event(
    event_name=EventName.FAVORITE_ADDED.value,
    occurred_at=now + timedelta(days=3),
    actor_type=ActorType.FAN.value,
    source=EventSource.FAN_APP.value,
    fan_id=str(blocked.fan_id),
    payload={
        "fan_id": str(blocked.fan_id),
        "cast_id": "cast-1",
        "favorite_source": "profile",
    },
)
UserBlock.objects.create(
    target=blocked,
    block_scope=BlockScope.ALL.value,
    block_reason="policy",
    is_risk_flag=False,
    effective_from=now,
    status=BlockStatus.ACTIVE.value,
    created_by=operator,
)

start, end = month_bounds(now.date())
payload = {
    "operatorToken": operator_token,
    "fanToken": fan_token,
    "start": start.date().isoformat(),
    "end": end.date().isoformat(),
    "expected": {
        "msfc": 1,
        "verified_visit_fans": 2,
        "safe_fan_continuation_rate": 0.5,
        "safety_reports_created": 1,
        "users_blocked": 1,
        "excluded_risk_fans": 1,
    },
}
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
print(f"SEEDED -> {out_path}")
