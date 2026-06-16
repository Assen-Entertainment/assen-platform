"""Seed a deterministic notification scenario for the E2E gate (ASS-113 v0).

Run against a throwaway sqlite DB via the Django shell::

    NOTIFICATION_SEED_OUT=/abs/path/.notification_seed.json \
      uv run python manage.py shell < ../e2e/seed_notification.py

Creates an operator and a fan account + tokens. The notification policy guard is
stateless (no model in v0), so the spec exercises the live policy + dispatch
endpoints directly; the fan token lets it assert the operator gate. Dev/E2E only.
"""

import json
import os

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

out_path = os.environ["NOTIFICATION_SEED_OUT"]

operator = Account.objects.create(role=Role.OPERATOR.value)
fan = Account.objects.create(role=Role.FAN.value)

payload = {
    "operatorToken": issue_token_pair(operator).access_token,
    "fanToken": issue_token_pair(fan).access_token,
}
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
print(f"SEEDED -> {out_path}")
