import { type Page, expect } from '@playwright/test';

// Shared helpers for the dev E2E journeys (fan + creator). Not a spec (no .web.spec suffix).
//
// ⚠️ 2026-07-18: the DEPLOYED dev now uses REAL social login (kakao/google/naver) — the mock
// social providers are GONE there. So socialLogin() below only works against a LOCAL mock
// stack (config.settings.dev). To run these against the deployed dev they must move to
// email/password auth, which needs a verified account — but the deployed demo neither echoes
// the verify token (EMAIL_VERIFY_RETURN_TOKEN is hardcoded False in base.py) nor logs it
// (prod-hardened JSON logging drops the extra token field). Enabling dev-automated E2E thus
// needs a small change: make EMAIL_VERIFY_RETURN_TOKEN env-driven and set it True on dev so
// signup self-serves the token. Until then, run these against a local mock stack. (mock
// KYC/payment/uploads stay open on demo — only social changed.)

export const BASE = process.env.WEB_BASE_URL ?? 'https://dev.assenent.com';

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
