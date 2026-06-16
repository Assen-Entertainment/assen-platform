# Assen E2E (Playwright)

Live, API-level end-to-end checks against a running local Assen stack. This is a
**Claude QA gate** run before merge — it is intentionally **not** wired into CI
(it needs a DB + a running server + Node). The spec suite is committed so it
compounds across issues; add a spec per feature surface as they ship.

## Why a live server (not just pytest)

`pytest` exercises the aggregation in-process; this suite proves the wired HTTP
surface — routing, auth (`operator_required`), serialization, and the contract —
against a real server, with deterministic seeded data.

## Run (WSL)

```sh
# 1. Bring up the API on a throwaway sqlite DB WITH the unmigrated-app tables.
#    (up-local.sh uses `migrate` without --run-syncdb, so it would miss them.)
cd server
export DJANGO_SETTINGS_MODULE=config.settings.dev
export DATABASE_URL='sqlite:////tmp/assen_kpi_e2e.sqlite3'
rm -f /tmp/assen_kpi_e2e.sqlite3
uv run python manage.py migrate --run-syncdb --noinput

# 2. Seed a deterministic scenario + tokens.
export KPI_SEED_OUT="$PWD/../e2e/.seed.json"
uv run python manage.py shell < ../e2e/seed_kpi.py

# 3. Serve, then run the suite.
uv run python manage.py runserver 127.0.0.1:8000 &   # background
cd ../e2e
npm install
KPI_SEED_OUT="$PWD/.seed.json" npx playwright test

# 4. Tear down: stop runserver, rm /tmp/assen_kpi_e2e.sqlite3 and .seed.json.
```

Artifacts: `playwright-report/` (HTML) and `test-results/` (traces) — both
git-ignored.

## Scope

- `tests/kpi-metrics.api.spec.ts` — ASS-112 operator KPI/MSFC endpoint:
  seeded-value assertions, the full field contract, counts-only/no-PII shape,
  operator gating (fan/anon → 401/403), inverted-window 422, and a v0 dashboard
  no-regression smoke.
- `tests/fan-signup.api.spec.ts` — ASS-98 fan phone-OTP signup + membership card:
  app body-token and web httpOnly-cookie delivery, consent/OTP 422s, auth gate.
- `tests/fan-report.api.spec.ts` — ASS-110 fan self-report intake
  (`POST /api/safety/fan-reports`): a signed-up fan files a report (receipt only,
  no internal classification), non-fan-reportable + unknown types → 422, auth
  gate (401/403), and a cross-surface check that the report reaches the operator
  queue with the narrative withheld (uses the seeded operator token).
- `tests/cast-profile.api.spec.ts` — ASS-92 cast profile management
  (`/api/cast/...`): the fail-closed consent gate (a profile is hidden until an
  operator publishes it *and* a manager grants the stage-name scope; a hidden
  profile 404s), per-scope gating (photo withheld even when the name is shown),
  the three access tiers (operator CRUD, manager-only consent, fan view), and the
  fan-role gate on the impression view. Needs `seed_cast.py` (operator + manager
  + fan tokens → `.cast_seed.json`):

  ```sh
  export CAST_SEED_OUT="$PWD/../e2e/.cast_seed.json"
  uv run python manage.py shell < ../e2e/seed_cast.py   # after step 1's migrate
  # then, alongside the suite: CAST_SEED_OUT="$PWD/.cast_seed.json" npx playwright test
  ```
- `tests/report-handling.api.spec.ts` — ASS-111 operator report-handling stats
  (`GET /api/safety/handling-stats`): the open queue bucketed by status/severity,
  resolved-in-window throughput, non-negative handling durations, the full field
  contract, counts-only/no-PII shape, operator gating (fan/anon → 401/403), and an
  out-of-range window → 422. Needs `seed_handling.py` (operator + fan tokens →
  `.handling_seed.json`):

  ```sh
  export HANDLING_SEED_OUT="$PWD/../e2e/.handling_seed.json"
  uv run python manage.py shell < ../e2e/seed_handling.py   # after step 1's migrate
  # then, alongside the suite: HANDLING_SEED_OUT="$PWD/.handling_seed.json" npx playwright test
  ```
- `tests/pos-link.api.spec.ts` — ASS-102 v0 operator POS Lite manual linking
  (`/api/operator/pos/...`): the seeded daily link coverage (POS 연결률 + 미연결
  목록 on an isolated date), duplicate-receipt rejection (400), the create→link
  round-trip on a fresh visit, and operator gating (fan/anon → 401/403). Scope is
  the POS-vendor-independent manual slice (P0_Scope_Reconciliation G-2); CSV
  import + daily reconciliation are held (OQ-C). Needs `seed_pos.py` (operator +
  fan tokens → `.pos_seed.json`):

  ```sh
  export POS_SEED_OUT="$PWD/../e2e/.pos_seed.json"
  uv run python manage.py shell < ../e2e/seed_pos.py   # after step 1's migrate
  # then, alongside the suite: POS_SEED_OUT="$PWD/.pos_seed.json" npx playwright test
  ```
- `tests/reservation.api.spec.ts` — ASS-109 v0 reservation/waitlist
  (`/api/operator/reservations` + `/api/fan/reservations`): the seeded operator
  daily list (counts-only/no-PII), a fan registering + listing their own (bearer,
  fan view omits operator fields), the **blocked-fan refusal** (the ASS-111
  reservation-block enforcement → 400), the operator confirm→cancel lifecycle, and
  the gates (staff token on the fan endpoint → 403; fan/anon on the operator
  surface → 401/403). Scope is the platform-internal manual slice; external/네이버
  sync, prepaid, and seat assignment are held (PRD P0 제외 / OQ-E). Needs
  `seed_reservation.py` (operator + fan + blocked-fan tokens → `.reservation_seed.json`):

  ```sh
  export RESERVATION_SEED_OUT="$PWD/../e2e/.reservation_seed.json"
  uv run python manage.py shell < ../e2e/seed_reservation.py   # after step 1's migrate
  # then: RESERVATION_SEED_OUT="$PWD/.reservation_seed.json" npx playwright test reservation.api.spec.ts --workers=1
  # (--workers=1: the lifecycle row locks serialise writes, which sqlite cannot do
  #  concurrently — "database is locked"; production Postgres handles it fine.)
  ```
- `tests/event-campaign.api.spec.ts` — ASS-107 v0 event announcements
  (`/api/operator/event-campaigns` + `/api/fan/event-campaigns` + `/api/fan/event-reservations`):
  operator sees draft+published; the fan list shows only published; a draft id is
  **404 to fans** (no existence leak); fan view/reserve/list-own/cancel; the
  **blocked-fan refusal** (400); a draft cannot be reserved (404); the operator
  publish/unpublish round-trip toggling fan visibility; and the gates (staff token
  on reserve → 403; fan/anon on the operator surface → 401/403). Scope stores **no
  price** (the price value is the approval-gated, deferred slice); seat/prepaid/
  external ticketing held (PRD F10 P0 제외). Needs `seed_event_campaign.py`
  (operator + fan + blocked-fan tokens, a published + a draft campaign →
  `.event_campaign_seed.json`); run with `--workers=1` (sqlite single-writer):

  ```sh
  export EVENT_CAMPAIGN_SEED_OUT="$PWD/../e2e/.event_campaign_seed.json"
  uv run python manage.py shell < ../e2e/seed_event_campaign.py   # after step 1's migrate
  # then: EVENT_CAMPAIGN_SEED_OUT="$PWD/.event_campaign_seed.json" npx playwright test event-campaign.api.spec.ts --workers=1
  ```
- `tests/notification.api.spec.ts` — ASS-113 v0 notification policy guard
  (`/api/operator/notifications/...`): the policy registry (allowed 4 + forbidden
  kinds), an allowed category dispatching (200), the fail-closed refusals (a
  named-forbidden category, an unknown category, a real-time presence field in
  `data`, and a non-future favourite-cast schedule → 422), and the operator gate
  (fan/anon → 401/403). Scope is the **policy guard + dispatch boundary**: no
  durable model/event and the in-memory mock adapter (real FCM is P5). Needs
  `seed_notification.py` (operator + fan tokens → `.notification_seed.json`):

  ```sh
  export NOTIFICATION_SEED_OUT="$PWD/../e2e/.notification_seed.json"
  uv run python manage.py shell < ../e2e/seed_notification.py   # after step 1's migrate
  # then: NOTIFICATION_SEED_OUT="$PWD/.notification_seed.json" npx playwright test notification.api.spec.ts
  ```
- `tests/visit-guide.api.spec.ts` — ASS-101 v0 visit guide / 이용 안내 CMS
  (`/api/operator/visit-guide` + `/api/visit-guide` + `/api/fan/visit-guide`):
  operator sees draft+published; the **public** list/detail show only published and
  are **unauthenticated** (pre-visit reading); a draft id is **404** to the public
  (no existence leak); a published section is **draft-only for edits** (400); the
  fan rule acknowledgement (records `rule_consent_given`); and the gates (staff
  token on ack → 403; fan/anon on the operator surface → 401/403). Scope stores
  **no price/menu value** (the approved values are the approval-gated, deferred
  slice). Needs `seed_visit_guide.py` (operator + fan tokens, a published + a draft
  section → `.visit_guide_seed.json`):

  ```sh
  export VISIT_GUIDE_SEED_OUT="$PWD/../e2e/.visit_guide_seed.json"
  uv run python manage.py shell < ../e2e/seed_visit_guide.py   # after step 1's migrate
  # then: VISIT_GUIDE_SEED_OUT="$PWD/.visit_guide_seed.json" npx playwright test visit-guide.api.spec.ts
  ```
