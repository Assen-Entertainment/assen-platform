"""Seed operator/manager/fan tokens for the cast-profile E2E gate (ASS-92).

Run inside the server's Django shell against a throwaway sqlite dev DB, e.g.::

    CAST_SEED_OUT=/abs/path/.cast_seed.json \
      uv run python manage.py shell < ../e2e/seed_cast.py

The cast spec needs all three role tokens: an operator creates/edits a profile, a
manager grants the per-scope portrait-rights consent, and a fan reads the gated
public view. Dev/E2E only — never run against a real DB.
"""

import json
import os

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

out_path = os.environ["CAST_SEED_OUT"]

operator = Account.objects.create(role=Role.OPERATOR.value)
manager = Account.objects.create(role=Role.MANAGER.value)
fan = Account.objects.create(role=Role.FAN.value)

payload = {
    "operatorToken": issue_token_pair(operator).access_token,
    "managerToken": issue_token_pair(manager).access_token,
    "fanToken": issue_token_pair(fan).access_token,
}
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
print(f"SEEDED -> {out_path}")
