import { type Page, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';

// Shared helpers for the dev E2E journeys (fan + creator). Not a spec (no .web.spec suffix).
//
// AUTH, TWO WAYS:
// - The DEPLOYED dev (dev.assenent.com) runs REAL social login (kakao/google/naver) — the mock
//   social providers are GONE there — so the deployed journeys authenticate via email/password.
//   `EMAIL_VERIFY_RETURN_TOKEN` is env-driven (config/settings/base.py, no longer hardcoded) and
//   is set True on dev (terraform dev.tfvars, 2026-07-18), so POST /api/fan/signup/email echoes
//   the verification token in its response and a journey can self-serve a verified session with
//   no real inbox — see bootstrapEmailFan / bootstrapEmailCreator.
// - A LOCAL mock stack (config.settings.dev) still ships the mock social providers, so
//   socialLogin() is kept for that path. USE_EMAIL_AUTH selects between them (email for the
//   deployed dev host, social for a localhost BASE); override with USE_EMAIL_AUTH=1|0.
// (mock KYC/payment/uploads stay open on demo — only social auth changed there.)

export const BASE = process.env.WEB_BASE_URL ?? 'https://dev.assenent.com';

/**
 * Auth mode toggle. Default: email verification for the deployed dev host (real social there),
 * mock social for a local mock stack (localhost/127.0.0.1). Force either with USE_EMAIL_AUTH=1|0.
 */
export const USE_EMAIL_AUTH =
  process.env.USE_EMAIL_AUTH != null
    ? process.env.USE_EMAIL_AUTH === '1' || process.env.USE_EMAIL_AUTH === 'true'
    : !/(?:localhost|127\.0\.0\.1)/.test(BASE);

// A dummy password for throwaway @assen.test email accounts (never a real secret).
const EMAIL_FAN_PASSWORD = 'assen-e2e-pass1';

// Group one run's throwaway accounts under a shared id; each call adds a fresh random suffix.
const RUN_ID = randomUUID().slice(0, 8);

// Distinct mock-social providers => distinct deterministic accounts (verified 2026-07-18:
// kakao/google/naver each mint a separate fan). Use different providers to get a creator
// and a fan that are NOT the same account.
export const SOCIAL_BUTTON: Record<string, string> = {
  kakao: '카카오로 계속하기',
  google: 'Google로 계속하기',
  naver: '네이버로 계속하기',
};

/** Log in via a mock social provider; resolves once the app lands on /discovery. */
export async function socialLogin(
  page: Page,
  provider: 'kakao' | 'google' | 'naver',
): Promise<void> {
  await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: SOCIAL_BUTTON[provider] }).click();
  await page.waitForURL(/\/discovery/, { timeout: 30_000 });
}

// The deployed dev host occasionally resolves to a stale Cafe24 IP (DNS flap). page.request
// runs on the Node side, so the browser's --host-resolver-rules override does NOT cover it —
// ride out an intermittent bad resolution (bogus host → non-JSON/404 or a connect error) with a
// few retries. Assertion failures re-throw once the attempts are exhausted.
async function withDnsRetry<T>(fn: () => Promise<T>, attempts = 4): Promise<T> {
  let lastErr: unknown;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
  }
  throw lastErr;
}

/**
 * Bootstrap a verified email fan against the deployed dev via the API, seeding the browser
 * context's cookie jar with a logged-in session. Playwright's `page.request` shares the browser
 * context cookie jar, so the assen_access / assen_session / assen_refresh cookies set by
 * verify-email(web:true) authenticate every subsequent `page.goto` — no UI login needed.
 *
 * Requires EMAIL_VERIFY_RETURN_TOKEN to be on server-side (dev), so signup echoes the token.
 * Returns the throwaway credentials in case a spec wants to re-login with them.
 */
export async function bootstrapEmailFan(page: Page): Promise<{ email: string; password: string }> {
  const rand = randomUUID().slice(0, 8);
  const email = `e2e-${RUN_ID}-${rand}@assen.test`;
  const password = EMAIL_FAN_PASSWORD;
  const nickname = `e2e-${rand}`;

  const token = await withDnsRetry(async () => {
    const resp = await page.request.post(`${BASE}/api/fan/signup/email`, {
      data: {
        email,
        password,
        nickname,
        consent_terms: true,
        consent_privacy: true,
        age_over_14: true,
      },
    });
    expect(resp.ok(), `signup/email → ${resp.status()}`).toBeTruthy();
    const body = (await resp.json()) as { verification_token?: string };
    expect(
      body.verification_token,
      'signup must echo verification_token (EMAIL_VERIFY_RETURN_TOKEN on for dev)',
    ).toBeTruthy();
    return body.verification_token as string;
  });

  await withDnsRetry(async () => {
    const resp = await page.request.post(`${BASE}/api/fan/verify-email`, {
      data: { token, web: true },
    });
    expect(resp.ok(), `verify-email → ${resp.status()}`).toBeTruthy();
  });

  return { email, password };
}

/**
 * Bootstrap a fresh email fan, clear the (mock) KYC gate, then promote to a creator with
 * `handle`. Becoming a creator is KYC-gated server-side (403 IdentityVerificationRequired
 * otherwise) and a fresh email account starts unverified, so ensureKyc runs before ensureCreator.
 * `handle` must be unique on the deployed dev — a fresh account cannot claim an already-registered
 * handle (^[a-z0-9_]+$, ≤32). Leaves the browser on /studio.
 */
export async function bootstrapEmailCreator(
  page: Page,
  handle: string,
  name: string,
): Promise<void> {
  await bootstrapEmailFan(page);
  await ensureKyc(page);
  await ensureCreator(page, handle, name);
}

/**
 * Ensure the logged-in fan is 본인인증(KYC)-verified. Idempotent: if already verified the
 * /verify page shows the "이미 완료" state and we return; otherwise accept the three consents
 * (via the ConsentGroup master "전체 동의") and submit. On demo the mock verifier passes.
 */
export async function ensureKyc(page: Page): Promise<void> {
  await page.goto(BASE + '/verify', { waitUntil: 'domcontentloaded' });
  // The page renders its consent form on the pre-session frame, then swaps to the
  // "already verified" state once the async /fan/me resolves. Give that a beat to settle
  // before deciding (networkidle is unreliable here — the app holds a notifications WS).
  await page.waitForTimeout(2500);
  if (await page.getByText('이미 본인인증이 완료되었어요').isVisible().catch(() => false)) return;
  await page.getByText('전체 동의', { exact: true }).click();
  await page.getByRole('button', { name: '본인인증하기' }).click();
  // Success fires a toast then immediately router.push(next) — the toast races navigation
  // and is flaky to assert. Assert the durable signal instead: we leave /verify for `next`.
  await page.waitForURL((u) => !new URL(u).pathname.startsWith('/verify'), { timeout: 20_000 });
}

/**
 * Ensure the logged-in user is a creator with `handle`. Idempotent: /become-creator
 * auto-redirects to /studio when the account is already a creator; otherwise fill the
 * handle+name form and submit. Leaves the browser on /studio.
 */
export async function ensureCreator(page: Page, handle: string, name: string): Promise<void> {
  await page.goto(BASE + '/become-creator', { waitUntil: 'domcontentloaded' });
  // Already a creator? the page's effect replaces to /studio.
  const onStudio = await page
    .waitForURL(/\/studio/, { timeout: 4_000 })
    .then(() => true)
    .catch(() => false);
  if (onStudio) return;
  await page.getByLabel('핸들').fill(handle);
  await page.getByLabel('크리에이터 이름').fill(name);
  await page.getByRole('button', { name: '크리에이터 페이지 열기' }).click();
  await page.waitForURL(/\/studio/, { timeout: 15_000 });
}
