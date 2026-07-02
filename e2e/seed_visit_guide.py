"""Seed a deterministic visit-guide scenario for the E2E gate (ASS-101 v0).

Run against a throwaway sqlite DB via the Django shell::

    VISIT_GUIDE_SEED_OUT=/abs/path/.visit_guide_seed.json \
      uv run python manage.py shell < ../e2e/seed_visit_guide.py

Creates operator/fan accounts + tokens, one **published** usage-rules section
(so a fan can acknowledge it and the public can read it) and one **draft**
section (so the spec can assert it is invisible publicly — 404, no existence
leak). Writes tokens + ids to ``$VISIT_GUIDE_SEED_OUT``. Dev/E2E only.
"""

import json
import os

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.visit_guide.models import GuideSectionType
from apps.visit_guide.services import create_section, publish_section

out_path = os.environ["VISIT_GUIDE_SEED_OUT"]

operator = Account.objects.create(role=Role.OPERATOR.value)
fan = Account.objects.create(role=Role.FAN.value)

operator_token = issue_token_pair(operator).access_token
fan_token = issue_token_pair(fan).access_token

rules = create_section(
    actor=operator,
    section_type=GuideSectionType.USAGE_RULES.value,
    title="이용 규칙",
    body="주류 비의존 · 별도 요청 금지 · 사적 연락 금지",
)
publish_section(section=rules, actor=operator)

draft = create_section(
    actor=operator,
    section_type=GuideSectionType.FIRST_VISIT_GUIDE.value,
    title="첫 방문 가이드 (작성 중)",
)

payload = {
    "operatorToken": operator_token,
    "fanToken": fan_token,
    "publishedSectionId": str(rules.id),
    "draftSectionId": str(draft.id),
}
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
print(f"SEEDED -> {out_path}")
