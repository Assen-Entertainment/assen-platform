"""Seed a deterministic RBAC scenario for the E2E gate (RBAC v0).

Run against a throwaway sqlite DB via the Django shell::

    RBAC_SEED_OUT=/abs/path/.rbac_seed.json \
      uv run python manage.py shell < ../e2e/seed_rbac.py

Creates the acting admin + a second admin (to demote), a target fan (to promote),
and operator/fan accounts for the gate checks. Writes tokens + ids to
``$RBAC_SEED_OUT``. Dev/E2E only.

HUMAN-REVIEW-REQUIRED: this exercises an authz surface (CONSTRAINTS #26).
"""

import json
import os

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

out_path = os.environ["RBAC_SEED_OUT"]

admin = Account.objects.create(role=Role.ADMIN.value)
second_admin = Account.objects.create(role=Role.ADMIN.value)
target_fan = Account.objects.create(role=Role.FAN.value)
operator = Account.objects.create(role=Role.OPERATOR.value)
fan = Account.objects.create(role=Role.FAN.value)

payload = {
    "adminToken": issue_token_pair(admin).access_token,
    "operatorToken": issue_token_pair(operator).access_token,
    "fanToken": issue_token_pair(fan).access_token,
    "adminId": str(admin.fan_id),
    "secondAdminId": str(second_admin.fan_id),
    "targetFanId": str(target_fan.fan_id),
}
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
print(f"SEEDED -> {out_path}")
