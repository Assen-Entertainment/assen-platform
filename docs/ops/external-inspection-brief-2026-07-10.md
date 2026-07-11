# Assen Platform — External Inspection Brief (2026-07-10)

> **For an external reviewer (human or AI agent) who has never seen this repo.**
> Part A gives you the context to inspect the platform competently. Part B is a
> ready-to-run *blindspot-hunting* prompt whose whole purpose is to surface the
> things the builders **don't know they don't know**. Read A, then run B.
>
> **Ground rule for the inspector:** treat every "verified / green / done" claim
> in our docs and commit messages as a *hypothesis to falsify*, not a fact. The
> most valuable output is a concrete, reproducible counterexample to something we
> believe is true.

---

## PART A — Inspection context

### A0. The one-paragraph truth

Assen is a **general-purpose subculture creator–fan platform** (think fan
memberships, posts, commerce/goods, events/cheki, studio for creators). It is a
**monorepo**: a Next.js web app, a Django + Django-Ninja API, a Flutter mobile
app, shared Dart packages, and a separate marketing landing site. It was built
**very fast by a fleet of AI coding agents** across many rounds. The single most
important thing to understand before inspecting: **it is a disciplined
"fail-closed mock skeleton."** The *boundaries* (auth gates, payment gate, KYC
gate, 19+ gate, upload gate, migrations gate) are carefully built, but the *real
implementations behind those boundaries are mostly deterministic mocks* — the
real integrations (payment gateway, identity verification, SMS OTP, cloud
storage, IAP) are deferred pending contracts. **An inspector who tests "does
payment work?" is testing a mock, not a PG.** Your job is partly to check that
the mock/real boundary is actually airtight and fail-closed as claimed.

### A1. Stack & repo layout

```
assen-platform/
├── web/            Next.js 15 · React 19 · TypeScript · Tailwind v4 · Radix · TanStack Query
│   ├── src/        app router, components/ui (design system), lib/api (client + mock)
│   └── e2e/        Playwright specs run in CI (journey / studio-upload / mobile-smoke / visual)
├── server/         Django 5.2 · django-ninja API · Postgres(prod)/sqlite(dev,test) · Celery · Channels(WS)
│   ├── apps/       domain apps (identity, content, uploads, commerce, ...)
│   └── config/     settings/{base,dev,test,demo,prod,test_pg}.py · api.py · errors · throttle
├── apps/assen_mobile/   Flutter app (go_router · Riverpod 3 · api_client)
├── packages/       core_tokens (design tokens codegen) · ui_kit (widgets + alchemist goldens)
│                   · api_client · test_fixtures
├── landing/        separate marketing site (assenent.com) — Vite; NOT the product
├── e2e/            top-level API-level Playwright specs (documented QA gate, not the CI web e2e)
├── docs/           ADRs, CONSTRAINTS.md, ops/, design/, backend/erd, deployment, onboarding
├── scripts/        bootstrap/doctor (Windows ps1), hooks/ (guard.py + pre-commit), up/smoke-local
├── .github/workflows/  ci · web-ci · e2e · sca · golden   (codeql removed — no GHAS)
└── justfile        canonical task runner (bootstrap/doctor/up/smoke/build/test)
```

Two things that trip people up:
- There are **two** `e2e/` trees. Top-level `e2e/` = API-level Playwright specs
  (a documented local QA gate, *not wired to CI*). The web e2e that **CI actually
  runs** lives in `web/e2e/` (`journey`, `studio-upload`, `mobile-smoke`, `visual`).
- `landing/` is the marketing site, not the product web app.

### A2. THE MOST IMPORTANT TABLE — the gate/mock flag matrix

Every decision gate is a boolean flag. **`base.py` hardcodes them all `False`
(fail-closed).** dev/test/demo turn the *mocks* on; **prod inherits base → all
off → the real path is refused (503/blocked) because no real backend is wired.**

| Flag | base (=prod) | dev | test | demo | What it gates |
|---|---|---|---|---|---|
| `ENABLE_MOCK_FAN_OTP` | **False** (hardcoded, not env) | True | True | True | SMS OTP login → deterministic mock code |
| `ENABLE_MOCK_KYC` | **False** | True | True | True | Identity/adult verification → deterministic mock |
| `ENABLE_MOCK_PAYMENT` | **False** | True | True | True | Payment tokenization/checkout → deterministic mock |
| `ENABLE_ADULT_CONTENT` | **False** | True | True | True | 19+ read exposure |
| `SERVE_LOCAL_MEDIA` | **False** | True | True | True | Upload endpoint accepts + local-serves media |
| `FAN_WRITE_THROTTLE_ENABLED` | **True** | (env) | False | (env) | Per-user write rate limit |

**prod is additionally fail-closed on secrets/infra**: `prod.py` uses a
schema-less `environ.Env()` so a missing `DJANGO_SECRET_KEY`,
`DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`, `CELERY_BROKER_URL`, or
`CELERY_RESULT_BACKEND` **raises at boot** instead of falling back to a dev
default. `DEBUG=False`, `SECURE_SSL_REDIRECT=True`.

**Inspector implication:** the interesting question is never "does the mock
work" — it's "**can the mock, or a mock-only affordance, ever reach a real/prod
context?**" and "**is every gate genuinely closed when the flag is False, on
every code path, including error/edge paths?**"

### A3. What is REAL vs MOCK (the boundary map)

- **Real:** the domain model & CRUD (posts, products, memberships, orders as
  records), authz/ownership, pagination (keyset), web/mobile UI, design system,
  rate limiting (Redis sliding-window), upload *validation* (magic-byte sniff +
  Pillow decode-verify + decompression-bomb guard), WS realtime (Channels),
  structured logging, CSP (report-only), migrations (real files, #25-gated).
- **Mock / deferred (need external contracts):** payment gateway (PG),
  KYC/identity, real SMS OTP, cloud object storage (S3/CDN) + media moderation,
  IAP (app-store billing), push (FCM/APNs), search relevance (Korean text uses
  multi-field `icontains`+Case ranking, not tsvector), i18n (single locale).
- **PII posture (claimed):** "0 PII stored." Error/parse paths are claimed to not
  embed PII. **Verify this** — see the blindspot prompt.

### A4. Environment & toolchain (Windows-first — real traps)

- **Python/server:** `uv`. On this workstation the venv is **`server/.venv-win`**
  (not `.venv`, which is a stale POSIX remnant). Set
  `UV_PROJECT_ENVIRONMENT=.venv-win`. `uv sync` fails if the dev server holds a
  `.pyd` lock → stop the server first, or `uv pip install --python
  .venv-win/Scripts/python.exe` for additive installs.
- **Node/web:** Node 22, `npm ci --legacy-peer-deps`.
- **Flutter:** installed at `C:\Users\daisy\flutter` and **not on the Git-Bash
  PATH** — invoke via PowerShell or the full path
  `C:\Users\daisy\flutter\bin\{flutter,dart}.bat`. `melos run test` needs flutter
  on the subprocess PATH.
- One-shot: `just bootstrap` / `just doctor` (Windows ps1 under `scripts/`).

### A5. Run / test / build — exact commands (these mirror CI)

**Server** (`server/`):
```
uv sync
uv run ruff check .
uv run mypy .
uv run pytest                       # sqlite; ~821 tests
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test
# real-Postgres pass: settings=config.settings.test_pg (needs a PG service)
```
**Web** (`web/`):
```
npm ci --legacy-peer-deps
npx tsc --noEmit
npm run lint
npm run build
npm run check:budget                # client JS bundle-size gate
npm run test:coverage               # vitest, ~229 tests
npm run build-storybook
```
**Flutter** (repo root):
```
dart pub get
dart run melos run format           # dart format --set-exit-if-changed .
dart run melos run analyze          # dart analyze --fatal-infos --fatal-warnings .
dart run melos run test             # ui_kit 189 (goldens skip #31) · app 143 · core_tokens 22 · test_fixtures 8 · api_client 3
```
**Live web e2e** (needs the stack up): Django (`dev` settings, `seed_demo`,
`SERVE_LOCAL_MEDIA on`, `runserver 127.0.0.1:8000`) + Next standalone
(`NEXT_PUBLIC_API_URL=/api`, built, `node .next/standalone/server.js`), then
`cd web && npx playwright test --project=chromium --project=mobile`. See
`e2e.yml` for the exact 1:1 sequence.

### A6. CI/CD map (`.github/workflows/`)

| Workflow | Trigger | What it gates |
|---|---|---|
| `ci.yml` | every PR/push | server(ruff+mypy+pytest+migcheck) · flutter(format+analyze+test+build smoke) · docker-compose boot smoke (path-gated) · gitleaks · harness-hook tests |
| `web-ci.yml` | web/** | tsc · lint · build · bundle-budget · vitest+coverage · storybook build · web docker build |
| `e2e.yml` | web/** or server/** | live Django+Next → Playwright (chromium journey + mobile smoke) |
| `sca.yml` | schedule/PR | Trivy fs CVE scan + CycloneDX SBOM (report-only) |
| `golden.yml` | ui_kit/** (verify) · **workflow_dispatch (generate)** | verify = no-op while goldens `skip:true`; generate = human (#31) 1-click that un-skips + `--update-goldens` + auto-commits Linux baselines |
| ~~codeql.yml~~ | — | **removed** — private repo lacks GitHub Advanced Security; secret/dep scanning is covered by gitleaks + Trivy |

### A7. Human gates & harness constraints (`docs/CONSTRAINTS.md`)

- **#24** lint+typecheck+test+build smoke on every PR.
- **#25** DB migrations are **human-gated** (`ALLOW_MIGRATIONS`); generated
  migration files must not be auto-edited by agents.
- **#26/#27** payment, auth, secrets, production changes are human gates.
- **#31** golden baselines & certain test edits are guarded by
  `scripts/hooks/guard.py`: `flutter test --update-goldens` and `goldens/`
  writes are **hard-blocked locally** (no env bypass) — golden baselines can only
  be minted by the CEO's `golden.yml` `workflow_dispatch` on Linux CI. Test edits
  need `ALLOW_TEST_EDIT`.
- Framing to keep honest: **"merged ≠ activated."** All decision-gate flags stay
  `False`; landing code behind a gate never turns the gate on.

### A8. Where the bodies are buried (non-obvious, from recent work)

- **Goldens** use `alchemist`; they render widgets through Alchemist's own
  harness, so a package-level `packages/ui_kit/test/flutter_test_config.dart`
  injects `AssenTheme.light()` — without it every widget null-checks on
  `Theme.of(context).extension<AssenColors>()!`. (This is why an un-skipped
  golden run once reported "191 passed, 42 failed".)
- **Upload validation** (`server/apps/uploads/images.py`): a file that passes the
  64-byte magic sniff can still be a corrupt/polyglot image — Pillow
  `verify()` (chunk CRC) is the real gate. A famous foot-gun: a *hand-crafted 1×1
  PNG literal* had a broken IDAT CRC and was correctly rejected.
- **e2e realism gap:** the web composer requires a **title**; a spec that filled
  only the body silently failed to publish. Client-side validation gates can
  make an e2e "hang" with no server error.
- **Historical hazard:** a PR was once merged into `dev` with **red CI**. Don't
  assume `dev` is green because it's the default branch — check.

---

## PART B — The blindspot-hunting prompt

> Paste the block below into a fresh, capable coding-agent session that has this
> repo checked out (or hand it to a senior human reviewer as a charter). It is
> written to find **unknown unknowns**, not to re-run our green checks.

```text
ROLE
You are an adversarial external auditor for the Assen platform (a fail-closed
"mock skeleton" creator–fan monorepo: Next.js web, Django-Ninja API, Flutter
mobile, shared Dart packages). The team believes the system is disciplined and
"green." Your job is to prove them wrong in specific, reproducible ways, and —
more importantly — to surface risks they have not even framed as questions.

PRIME DIRECTIVE
Do not confirm what we already track. Hunt for BLINDSPOTS: things that are true
about this system that no test, doc, or person here has checked. For every
finding, give (1) the exact file:line or command, (2) a concrete reproduction or
counterexample, (3) the blast radius if real, (4) confidence, and (5) the
smallest fix or the smallest experiment that would confirm/deny it. Rank by
"scariest-if-true × plausibility", not by how easy it was to find.

FALSIFY THESE CLAIMS (each is a hypothesis, not a fact)
1. "Fail-closed." Every decision gate (ENABLE_MOCK_FAN_OTP / _KYC / _PAYMENT,
   ENABLE_ADULT_CONTENT, SERVE_LOCAL_MEDIA) is False in base/prod and cannot be
   bypassed. → Find any code path, env override, test-only affordance, seed, or
   mock module that could execute in a prod/real context, or any gate that is
   checked in one place but not another (e.g. read vs write, list vs detail,
   API vs WS vs Celery task vs management command vs admin).
2. "Mock ≠ real, and they're isolated." → Find where mock data, mock tokens,
   deterministic OTP/KYC/payment results, demo seed accounts (e.g. 010-000...),
   or `mock`-mode branches could leak into a live build, a real DB, logs, or a
   response a real user could see. Check bundle tree-shaking of mock code in the
   web client and the mobile app.
3. "0 PII stored / no PII in errors, logs, analytics, URLs." → Try to make PII
   (phone, name, address, tokens, Bearer, session) appear in: exception
   messages, DRF/Ninja validation errors, structured logs, Sentry payloads,
   analytics events, query strings, media EXIF/filenames, WS frames, or golden
   images. The upload path mints UUID filenames — verify nothing upstream keeps
   the original name/EXIF.
4. "Authz is enforced." → Hunt IDOR / broken object-level auth: can a fan hit a
   creator-owner endpoint; can user A read/mutate user B's orders, posts,
   drafts, memberships, notifications, studio stats; are ownership checks
   present on EVERY mutating and detail endpoint including WS subscribe and
   Celery-triggered actions; is the WS Origin guard (CSWSH) actually applied.
5. "Uploads are safe." → Beat the image gate: polyglots, SVG-as-PNG,
   decompression bombs within the dimension cap, content-type vs magic
   mismatch, path traversal via crafted names, oversize via chunked/absent
   size, and whether SERVE_LOCAL_MEDIA=False truly refuses (503) on every path.
6. "Rate limiting / throttle works." → Bypass the per-user write throttle:
   multi-worker races, Redis-down fallback behavior (does it fail open?), key
   collision, retraction/idempotency edge cases, cost of the sliding window.
7. "Security headers / CSP protect the app." → CSP is report-only (does nothing
   yet); find XSS/HTML-injection sinks that report-only wouldn't stop, missing
   nosniff on any media path, cookie flags (SameSite/HttpOnly/Secure), and
   whether prod's boot-time env requirements can be silently satisfied.
8. "Tests mean it works." → Find tests that assert nothing meaningful, mock away
   the very thing under test, are skipped/`skip:true` and hide a real bug (the
   goldens were skipped for weeks), are platform-only (pass on the dev's Windows,
   would fail on Linux CI, or vice-versa), or are flaky. Find code with 0
   coverage on a security-critical path (server coverage ~61%, web ~61%).
9. "The docs/commit claims are accurate." → Pick 10 "verified/green/done" claims
   from docs/ops/*, memory, and commit messages and try to falsify each against
   the actual code and a fresh clean run.

HUNT FOR AI-SLOP (this code was written by a fleet of AI agents)
- 21 near-identical widgets / N near-identical endpoints: find the copy-paste
  bug that exists in one but not the others.
- Comments that describe behavior the code no longer has; docstrings that
  overstate guarantees; "defense-in-depth" that is actually dead code.
- Over-abstraction that hides a bug; a shared helper whose one caller needs
  different behavior; error handling that swallows the real error
  (`except Exception: return False/None`) and turns a bug into silent wrong data.
- Numbers that don't reconcile (test counts, coverage, bundle budgets) between
  docs and reality.

UNKNOWN-UNKNOWN META PASS (do this last, explicitly)
Answer these in writing, doing new investigation for each — the goal is to name
risks we have not framed:
- "What is the scariest thing that could be true about this system that no one
  here has checked?" Then go check it.
- "What does every builder here assume is true that a hostile or careless user
  would violate?" Enumerate the assumptions, then break three of them.
- "If this launched to real traffic and real money tomorrow, what breaks first,
  silently?" Trace one end-to-end money/identity path and find the silent
  failure.
- "What exists in the repo that no test, doc, or CI job even mentions?" (orphan
  endpoints, dead flags, unreferenced env vars, admin actions, management
  commands, WS message types, feature flags). List them; probe the riskiest.
- "Where does the mock skeleton lie to itself?" — a mock that returns success so
  convincingly that a real integration would behave differently and no one would
  notice until production.

METHOD
- Prefer a clean clone + the documented commands (Part A §A5) so you reproduce
  CI's environment, not the dev's workstation. Note any step that only works on
  Windows or only on Linux.
- Diff intent vs behavior: read the docstring/comment/commit claim, then read
  the code, then run it.
- When you can't run something, say so and give the exact experiment that would
  settle it. Never assert a green result you didn't observe.

OUTPUT
A ranked findings list (scariest-if-true first). Each: title · file:line ·
repro/counterexample · blast radius · confidence · smallest confirming
experiment or fix. End with a short "Unknown-unknowns" section naming risks you
newly framed, and a "What I could NOT check and why" section (this last section
is itself a map of our blindspots).
```

---

## PART C — Supporting deep-dive prompts (optional, per domain)

Use these to parallelize the audit across reviewers/agents; each is scoped so a
single agent can go deep.

- **Auth/authz:** "Enumerate every mutating and detail endpoint across
  `server/apps/**` (HTTP, WS consumers, Celery tasks, management commands, admin
  actions). For each, state the ownership/permission check and show the test
  that proves a non-owner is rejected. Report any endpoint with no such test."
- **Gate integrity:** "For each flag in the A2 matrix, grep every read site and
  prove the code is fail-closed when False on every path (read/write/list/detail
  /WS/task). Report any single-site check or env override that could open it."
- **Data/PII:** "Instrument or trace one full OTP-login → KYC → checkout →
  order path and capture everything written to logs, Sentry, analytics, DB, and
  responses. List every field; flag anything that is or could become PII."
- **Web client honesty:** "Build the web app in live mode and prove the mock
  data module and demo-only copy are tree-shaken out of the production bundle.
  Show the bundle bytes."
- **Mobile parity:** "Compare each mobile screen's server contract parsing
  against the web client's for the same endpoint; find where they disagree
  (fields, error handling, gate respect)."
- **Migrations/data safety:** "Given the #25 human gate, verify the committed
  migrations reproduce the models exactly (`makemigrations --check`) on real
  Postgres (`test_pg`), and that no migration is destructive or order-dependent
  in a way that would corrupt real data on a real deploy."

---

## PART D — Ground-truth anchors (verify our claims against these)

| Claim | Anchor to check it against |
|---|---|
| Gate flags fail-closed | `server/config/settings/base.py` (all False), `dev/test/demo.py` (mocks True), `prod.py` (schema-less `_required` Env) |
| Upload security boundary | `server/apps/uploads/images.py`, `server/apps/uploads/api.py`, `server/apps/uploads/tests.py` |
| Test counts | server `uv run pytest` ; web `npm run test:coverage` ; flutter `dart run melos run test` |
| Coverage | web `web/coverage/` (Statements ~61%); server — measure it (claimed ~??, verify) |
| CI truth | `.github/workflows/{ci,web-ci,e2e,sca,golden}.yml` |
| Human gates | `docs/CONSTRAINTS.md`, `scripts/hooks/guard.py` |
| Production-readiness backlog | `docs/ops/production-readiness-2026-07-09.md` (Linear ASS-261..283) |
| Prior validation dossier | `docs/ops/validation-dossier-2026-07-10.md` |

> If any anchor contradicts a claim, **the contradiction is the finding.** Report
> it.
