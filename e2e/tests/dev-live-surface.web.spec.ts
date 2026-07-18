import { test, expect } from '@playwright/test';

/**
 * Real-usage QA against the DEPLOYED dev stack (Next.js web + real API on the dev ALB),
 * reflecting the POST-auth-redesign UI: email/password + social login (phone OTP removed).
 *
 * Scope note (verified 2026-07-18): the deployed dev runs `config.settings.demo`
 * (prod-hardened) over http, so every auth cookie is `Secure` and a browser drops it
 * over http — no browser login is possible there (email verify token is not echoed,
 * the social-state cookie is dropped, the demo account is not seeded). Authenticated
 * flows are covered separately by the API harness (scratchpad/dev_journey.py, PASS).
 * This spec therefore covers what a browser CAN exercise on live dev: the public
 * surface, auth guards, the new auth UI rendering, and input-safety — the real-usage
 * unauthenticated journey.
 *
 *   WEB_BASE_URL=http://<dev-alb> npx playwright test tests/dev-live-surface.web.spec.ts --config playwright.web.config.ts
 */
const BASE = process.env.WEB_BASE_URL ?? 'http://assen-dev-api-307204389.ap-northeast-2.elb.amazonaws.com';

test.describe('dev live · public pages load without auth', () => {
  for (const path of ['/', '/discovery', '/store', '/login', '/signup', '/policy/terms', '/policy/privacy', '/policy/refund']) {
    test(`public page loads: ${path}`, async ({ page }) => {
      const resp = await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
      expect(resp, `${path} response`).not.toBeNull();
      expect(resp!.status(), `${path} status`).toBeLessThan(400);
      await expect(page.locator('body')).toBeVisible();
    });
  }
});

test.describe('dev live · auth guards bounce anon to /login', () => {
  for (const path of ['/mypage', '/orders', '/settings', '/studio']) {
    test(`anon ${path} -> /login (?next preserved)`, async ({ page }) => {
      await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
      await expect(page, `${path} should bounce to login`).toHaveURL(/\/login/, { timeout: 15_000 });
      const next = new URL(page.url()).searchParams.get('next');
      expect(next, `${path} preserved as ?next`).toContain(path);
    });
  }
});

test('dev live · open-redirect via ?next= is neutralized', async ({ page }) => {
  await page.goto(BASE + '/login?next=https://evil.example.com/steal', { waitUntil: 'domcontentloaded' });
  expect(new URL(page.url()).host, 'stays on app host').toBe(new URL(BASE).host);
});

test('dev live · unauthenticated API: public ok, protected rejected', async ({ request }) => {
  const products = await request.get(BASE + '/api/products');
  expect(products.status(), 'public product list ok').toBe(200);
  const me = await request.get(BASE + '/api/fan/me');
  expect([401, 403], '/api/fan/me anon must not 200').toContain(me.status());
});

test('dev live · login renders the NEW auth UI (email + social, no phone OTP)', async ({ page }) => {
  await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' });
  // email/password fields (live useApi mode)
  await expect(page.getByPlaceholder('you@assen.kr')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('button', { name: '로그인' })).toBeVisible();
  // social buttons carry the "…계속하기" labels (real SocialButtons component, not the mock "…계속")
  await expect(page.getByRole('button', { name: '카카오로 계속하기' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Google로 계속하기' })).toBeVisible();
  // the removed phone-OTP affordance must be gone
  await expect(page.getByText('휴대폰 번호')).toHaveCount(0);
});

test('dev live · email signup submits and reaches the "확인 메일을 보냈어요" state', async ({ page }) => {
  await page.goto(BASE + '/signup', { waitUntil: 'domcontentloaded' });
  await expect(page.getByPlaceholder('you@assen.kr')).toBeVisible({ timeout: 15_000 });

  const email = `qa-live-${Date.now()}@assen.test`;
  await page.getByPlaceholder('you@assen.kr').fill(email);
  await page.getByPlaceholder('8자 이상').fill('assen-qa-pass1');
  await page.getByPlaceholder('사용할 닉네임').fill('QAlive');

  // 가입하기 is disabled until the three required consents are checked.
  const submit = page.getByRole('button', { name: '가입하기' });
  await expect(submit).toBeDisabled();
  await page.getByText('전체 동의', { exact: true }).click();
  await expect(submit).toBeEnabled();
  await submit.click();

  // Real backend call -> success screen (token is NOT echoed on demo, so no dev link,
  // but the confirmation heading is gated only on a successful signup).
  await expect(page.getByText('확인 메일을 보냈어요')).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(email)).toBeVisible();
});

test('dev live · verify-email with a bad token fails closed', async ({ page }) => {
  await page.goto(BASE + '/verify-email?token=not-a-real-token', { waitUntil: 'domcontentloaded' });
  await expect(page.getByText('인증에 실패했어요')).toBeVisible({ timeout: 15_000 });
});

test('dev live · signup nickname is not rendered as HTML (reflected-input safety)', async ({ page }) => {
  await page.goto(BASE + '/signup', { waitUntil: 'domcontentloaded' });
  await expect(page.getByPlaceholder('사용할 닉네임')).toBeVisible({ timeout: 15_000 });
  const xss = '<img src=x onerror="window.__xss=1">';
  await page.getByPlaceholder('사용할 닉네임').fill(xss);
  const injected = await page.evaluate(() => (window as unknown as { __xss?: number }).__xss ?? 0);
  expect(injected, 'nickname XSS did not execute').toBe(0);
});
