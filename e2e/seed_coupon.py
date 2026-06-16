"""Seed a deterministic coupon/point scenario for the E2E gate (ASS-108 v0).

Run against a throwaway sqlite DB via the Django shell::

    COUPON_SEED_OUT=/abs/path/.coupon_seed.json \
      uv run python manage.py shell < ../e2e/seed_coupon.py

Creates operator/fan/blocked-fan accounts + tokens, an active coupon for the fan
(to redeem), and a separately-blocked fan (active FANDOM_FEATURE block) with their
own active coupon (so the spec can assert a blocked redeem is refused). Writes
tokens + ids to ``$COUPON_SEED_OUT``. Dev/E2E only.
"""

import json
import os

from apps.coupon.models import CouponType
from apps.coupon.services import issue_coupon
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.safety.models import BlockScope, UserBlock
from django.utils import timezone

out_path = os.environ["COUPON_SEED_OUT"]

operator = Account.objects.create(role=Role.OPERATOR.value)
fan = Account.objects.create(role=Role.FAN.value)
blocked_fan = Account.objects.create(role=Role.FAN.value)

operator_token = issue_token_pair(operator).access_token
fan_token = issue_token_pair(fan).access_token
blocked_fan_token = issue_token_pair(blocked_fan).access_token

UserBlock.objects.create(
    target=blocked_fan,
    block_scope=BlockScope.FANDOM_FEATURE.value,
    block_reason="policy_violation",
    effective_from=timezone.now(),
    created_by=operator,
)

active_coupon = issue_coupon(fan=fan, coupon_type=CouponType.REVISIT.value, actor=operator)
blocked_coupon = issue_coupon(
    fan=blocked_fan, coupon_type=CouponType.REVISIT.value, actor=operator
)

payload = {
    "operatorToken": operator_token,
    "fanToken": fan_token,
    "blockedFanToken": blocked_fan_token,
    "fanId": str(fan.fan_id),
    "blockedFanId": str(blocked_fan.fan_id),
    "activeCouponId": str(active_coupon.id),
    "blockedCouponId": str(blocked_coupon.id),
}
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
print(f"SEEDED -> {out_path}")
