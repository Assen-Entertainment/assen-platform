# Audit Remediation Plan — External Blindspot Audit (2026-07-10)

**Verdict: Production activation BLOCKER.** An external adversarial audit (which
we commissioned via `external-inspection-brief-2026-07-10.md`) found that **a
green CI does not satisfy the core requirements** — fail-closed gating, mock
isolation, PII boundary, and client-contract completeness. Every critical path
below passed the existing CI. **Product code has NOT been changed;
release / payment / privacy decisions are left pending approval.**

- Tracking epic: **ASS-284**. Per-finding issues: **ASS-285 … ASS-296**.
- Source brief: `docs/ops/external-inspection-brief-2026-07-10.md`.
- Lesson to bake in: *"CI green / verified" is not evidence of contract
  satisfaction.* Gate integrity is only proven by cross-path checks
  (read / write / WS / task / entrypoint).

---

## 1. Decision memo — human gates (require CEO / Privacy Owner sign-off)

These change product behavior on a **human-gated** boundary; no code moves until
signed off.

> **Status — 2026-07-11:** the decision authority reviewed the original proposals
> and returned **MODIFY**. The payment / identity human gates are **NOT open**;
> the specs below are the corrected records of what MAY be built *once an approval
> is recorded*. Nothing has been implemented.

### D1 · Payment containment (`ASS-286`; children `ASS-297`, `ASS-298`) — gate #26
Corrected from the original proposal:
- **Gate on `ENABLE_MOCK_PAYMENT` only — NOT `payment_tokenizer()`.** The tokenizer
  only tokenizes a card (no authorize/capture) and the order payload carries no
  payment method, so tokenizer-presence is not a "paid" signal — a real tokenizer
  would still let PAID happen with no money.
- `ENABLE_MOCK_PAYMENT=False` ⇒ `create_order`, `subscribe`, **paid tier change**
  all return coded `503 ErrorCode.PAYMENTS_UNAVAILABLE` with **zero side effects**
  (no Order/OrderItem/Subscription/stock/notification change). `True` ⇒ dev/test
  explicit mock only. Scope is "block false paid/active", **not** "PG-ready".
- **Do NOT auto-pass `amount==0`.** Price is display-only and defaults to 0, so a
  zero can be an unset placeholder, not an approved free product; coupon-100% is
  not in the order contract. Free flows require an explicit free-grant (`ASS-297`).
- Close the bypasses + regress: tier change (`membership/api.py:503`) and the
  idempotency early-return (`commerce/api.py:770`) that precedes any guard.
- Provenance is a **separate** step (`ASS-298`, after #25): states
  free/mock/external/legacy_unknown + a `PaymentAttempt` ledger before real PG.

### D2 · Privacy (`ASS-287`) — A conditional tech-approval, B blocked
Existing draft policies already govern this; the code got ahead of them.
- **A-1 `ENABLE_SHIPPING_CHECKOUT`** (conditional): hardcoded False in
  base/prod/demo (no env override), test-fixture-only True. Server emits a
  `checkout_available` / `unavailable_reason` **capability** the web consumes (no
  duplicated Django/Next flag). Closes goods CTA, `/checkout?item=<goods>`,
  param-less `/checkout` fallback, non-auth PII form, no-URL mock success, direct
  `POST /api/orders`, unverified completion screen; free goods blocked too; hide
  the "무료배송" copy.
- **A-2 phone HMAC** (conditional): dedicated `PHONE_IDENTIFIER_HMAC_KEY`
  (≠ `SECRET_KEY`), ≥32B per-env, `v1:<base64url(HMAC-SHA256)>`, prod fail-close on
  missing/short/unknown-version; 0 real accounts ⇒ reset/reseed, else OTP-gated
  dual-read (current→previous→legacy SHA) + in-txn rekey, no auto-merge. Remains
  pseudonymous PII, not anonymization.
- **A-3** (with `ASS-291`): drop address from shipping **list** DTOs
  (`OrderOut`/`OrderItemOut`), expose minimally only in the owner's own detail.
- **B — blocked until the authority decides:** retention/deletion values, postal-
  cheki sale approval, consent/policy wording, whether P0 collects shipping PII.

### D3 · Release freeze
Until D1 and D2 are resolved and the ungated waves land, **do not activate for
real traffic / real money.**

---

## 2. Remediation sequencing

Waves ordered by blast-radius and gate status. Ungated items are all
fail-closed/safety hardening and can start on a simple go-ahead.

| Wave | Items (Linear) | Gate | Note |
|---|---|---|---|
| **0 — Decide** | `ASS-286` payment · `ASS-287` privacy | 🔒 CEO / Privacy Owner | Blocks release; decide first |
| **1 — Ungated criticals + security hardening** | `ASS-285` entrypoint · `ASS-289` web mock/forged · `ASS-291` PII log paths · `ASS-292` WS revoke · `ASS-293` upload EXIF | none | Highest risk; safe direction |
| **2 — Ungated completeness + CI** | `ASS-288` demo seed · `ASS-290` OpenAPI drift · `ASS-294` mobile release · `ASS-295` prod rate-limit · `ASS-296` gate/completeness bundle | none | Lower blast radius |

Every fix is a separate authoring pass + a **separate** verify/review pass, with
a false-state regression test, then a per-discipline PR into `dev`. Re-verify
each finding against the code before fixing (the audit cites file:line; #1/#2/#3
were independently re-confirmed here).

---

## 3. Findings → remediation (full)

| # | Linear | Sev | Gate | Root cause (file) | Minimal fix | Acceptance |
|---|---|---|---|---|---|---|
| 1 | ASS-285 | Crit | — | asgi/wsgi/celery.py `setdefault(...,"config.settings.dev")` | require explicit `prod` at every ops entrypoint; boot-fail on missing/dev/demo | import w/o env fails; prod-only regression test |
| 2 | ASS-286 | Crit | 🔒pay | `commerce`/`membership` never read `ENABLE_MOCK_PAYMENT` | coded 503 before real PG auth + false-flag test | flag False ⇒ order/sub blocked |
| 3 | ASS-287 | Crit | 🔒priv | `commerce/models.py:153-157` stored PII; weak phone hash | hide checkout; policy; HMAC/pepper (no model change pre-signoff) | policy signed; identifier not brute-forceable |
| 4 | ASS-288 | High | — | `demo.py` inherits prod DB; `seed_demo` unguarded | require `ALLOW_DEMO_SEED` + demo-DB sentinel; refuse in prod | prod/real-DB seed refused |
| 5 | ASS-289 | High | — | checkout proceeds w/o entity; mock finance in prod bundle | live-mode 404/block; gate studio finance; tree-shake | no mock finance in live bundle; forged URL 404 |
| 6 | ASS-290 | High | — | OpenAPI snapshot drift 25; clients use hand types | CI schema diff gate; wire generated DTO | drift fails CI; ≥1 domain on gen DTO |
| 7 | ASS-291 | High | — | X-Request-ID trust; cast_id; mobile parser; safety query | ID grammar; opaque-ID verify; key-only parse; reason codes; scrubber | PII-absent regression per path |
| 8 | ASS-292 | High | — | WS auth handshake-only; no re-check | expiry timer / revoke broadcast / re-verify pre-delivery | revoke drops live socket |
| 9 | ASS-293 | High | — | `uploads/api.py:202` stores original bytes | canonical re-encode (strip EXIF/GPS); early ingress limit | stored file EXIF-free; early length reject |
| 10 | ASS-294 | High | — | mobile release builds w/o base URL | build-time assertion; API handshake smoke; iOS lane | no-URL release fails |
| 11 | ASS-295 | Med-Hi | — | `base.py:69` memory limiter default in prod | require shared backend + proxy hops in prod | prod fails w/o shared limiter |
| 12 | ASS-296 | Med | — | adult count leak; always-mock notify; unused flags; mobile scheme; missing IDOR tests | per-item gate/verify/test | each sub-item covered |

---

## 4. Falsified "green / done" claims (record)

| Prior claim | Verdict |
|---|---|
| All mocks are flag-gated | **False** (order / subscription / push) |
| prod fails to boot on missing secrets | Only if `prod` is imported explicitly; default entrypoints fall back to dev |
| Zero stored PII | **False** |
| live web mock tree-shaken | **False** (checkout/studio mock in production bundle) |
| OpenAPI snapshot is canonical | **False** (25 structural diffs; generated types unused) |
| Server tests "~821" | 824 collected / 817 passed / 7 skipped |
| Flutter 3-target CI | web + Android debug only; no iOS |
| CI green ⇒ prod contract met | **False** (all criticals passed CI) |

The Production-Readiness **project description** still lists "already solid,
no rework: secrets fail-closed · Sentry PII scrubber" — both partially
falsified here; update it.

---

## 5. Not tested by the audit (still-open blindspots)

Real PostgreSQL/Redis multi-worker, ECS/task definitions, ALB logs, real Sentry
transport, S3/CDN, the live Playwright stack, iOS, GitHub branch protection /
current remote CI, external payment/KYC/SMS/IAP, a Linux clean clone, and the
golden workflow. These are the next places to look once Waves 0–2 land.

---

*Owner note:* the auditor logged two items (AI false-completion; privacy
near-miss) as **open** in `Company-OS/07_LLM/LLM_Mistake_Ledger.md`. They stay
open until the underlying product defects (ASS-285…296) are fixed, not merely
filed.
