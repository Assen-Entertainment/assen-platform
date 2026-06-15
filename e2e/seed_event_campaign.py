"""Seed a deterministic event-campaign scenario for the E2E gate (ASS-107 v0).

Run against a throwaway sqlite DB via the Django shell::

    EVENT_CAMPAIGN_SEED_OUT=/abs/path/.event_campaign_seed.json \
      uv run python manage.py shell < ../e2e/seed_event_campaign.py

Creates operator/fan accounts + tokens, a separately-blocked fan (active
fandom-feature block), one **published** campaign and one **draft** campaign on a
future date. The draft id lets the spec assert it is invisible to fans (404, no
existence leak). Writes the tokens + ids to ``$EVENT_CAMPAIGN_SEED_OUT`` for the
Playwright spec. Dev/E2E only.
"""

import json
import os
from datetime import timedelta

from django.utils import timezone

from apps.event_campaign.services import create_campaign, publish_campaign
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.safety.models import BlockScope, UserBlock

out_path = os.environ["EVENT_CAMPAIGN_SEED_OUT"]

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

starts_at = timezone.now() + timedelta(days=30)
published = create_campaign(
    actor=operator, title="Seeded Birthday Live", starts_at=starts_at, event_type="birthday"
)
publish_campaign(campaign=published, actor=operator)
draft = create_campaign(
    actor=operator, title="Seeded Draft", starts_at=starts_at, event_type="theme_day"
)

payload = {
    "operatorToken": operator_token,
    "fanToken": fan_token,
    "blockedFanToken": blocked_fan_token,
    "fanId": str(fan.fan_id),
    "publishedCampaignId": str(published.id),
    "draftCampaignId": str(draft.id),
}
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
print(f"SEEDED -> {out_path}")
