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
