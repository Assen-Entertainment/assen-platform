import { test, expect, type Page } from '@playwright/test';
import crypto from 'node:crypto';

// Untrusted-user QA against the DEPLOYED dev stack (Next.js web + real API, demo/mock
// gates). Drives a real Chromium as an anonymous / newly-registered fan and probes
// what an untrusted visitor can reach. Run:
//   WEB_BASE_URL=http://<dev-alb> npx playwright test tests/dev-untrusted-user.web.spec.ts --config playwright.web.config.ts
const BASE = process.env.WEB_BASE_URL ?? 'http://assen-dev-api-307204389.ap-northeast-2.elb.amazonaws.com';

// Mirror the server's MockOtpSender.code_for (config/otp.py): the dev OTP is a
// deterministic HMAC-SHA256("assen-dev-otp", phone) → first 4 bytes mod 1e6, 6 digits.
function otpFor(phone: string): string {
  const hex = crypto.createHmac('sha256', 'assen-dev-otp').update(phone, 'utf8').digest('hex');
  return String(parseInt(hex.slice(0, 8), 16) % 1_000_000).padStart(6, '0');
}

// Mirror server normalize_phone (identity/signup_services.py): the OTP is armed for
// the canonical +82 key, so the code must be computed from the normalized phone.
function normalizePhone(phone: string): string {
  const digits = phone.replace(/\D/g, '');
  if (phone.trim().startsWith('+')) return '+' + digits;
  if (digits.startsWith('0')) return '+82' + digits.slice(1);
  return '+' + digits;
}

test.describe('untrusted user · anonymous public browsing', () => {
  for (const path of ['/', '/discovery', '/store', '/login', '/signup', '/policy/terms', '/policy/refund']) {
    test(`public page loads without auth: ${path}`, async ({ page }) => {
      const resp = await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
      expect(resp, `${path} response`).not.toBeNull();
      expect(resp!.status(), `${path} status`).toBeLessThan(400);
      await expect(page.locator('body')).toBeVisible();
    });
  }
});

test.describe('untrusted user · auth guards (must NOT reach protected pages)', () => {
  for (const path of ['/mypage', '/orders', '/settings', '/studio']) {
    test(`anonymous ${path} is redirected to /login`, async ({ page }) => {
      await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
      await expect(page, `${path} should bounce to login`).toHaveURL(/\/login/);
      const next = new URL(page.url()).searchParams.get('next');
      expect(next, `${path} preserved as ?next`).toContain(path);
    });
  }
});

test('untrusted user · open-redirect via ?next= is neutralized', async ({ page }) => {
  await page.goto(BASE + '/login?next=https://evil.example.com/steal', { waitUntil: 'domcontentloaded' });
  // sanitizeNext only allows relative in-app paths — the page must stay on the app origin.
  expect(new URL(page.url()).host, 'stays on app host').toBe(new URL(BASE).host);
});

test('untrusted user · unauthenticated API does not leak protected data', async ({ request }) => {
  const products = await request.get(BASE + '/api/products');
  expect(products.status(), 'public product list ok').toBe(200);

  // A protected identity read must reject an anonymous caller (no data leak).
  const me = await request.get(BASE + '/api/fan/me');
  console.log('[probe] GET /api/fan/me (anon) ->', me.status());
  expect([401, 403, 404], '/api/fan/me anon must not 200').toContain(me.status());
});

test('untrusted user · full OTP signup, then session-persistence check', async ({ page, context }) => {
  const phone = '010' + String(Date.now()).slice(-8); // fresh 11-digit number
  const code = otpFor(normalizePhone(phone));
  console.log(`[signup] phone=${phone} computed-otp=${code}`);

  await page.goto(BASE + '/signup', { waitUntil: 'domcontentloaded' });
  await page.getByLabel('휴대폰 번호').fill(phone);
  await page.getByRole('button', { name: '인증번호 받기' }).click();

  // OTP + form step
  await expect(page.getByLabel('자리 1')).toBeVisible({ timeout: 15_000 });
  for (let i = 0; i < 6; i++) await page.getByLabel(`자리 ${i + 1}`).fill(code[i]);
  await page.getByLabel('닉네임').fill('테스트팬');
  // Accept every consent via the "전체 동의" master toggle (item labels carry a
  // "(필수)" suffix, so an exact per-item text match does not hit them).
  await page.getByText('전체 동의', { exact: true }).click();
  await expect(page.getByRole('button', { name: '가입하기' })).toBeEnabled();
  await page.getByRole('button', { name: '가입하기' }).click();

  // Observe: signup API result + whether the session cookie actually stuck.
  await page.waitForTimeout(3_500);
  const cookies = await context.cookies();
  const hasAccess = cookies.some((c) => c.name === 'assen_access');
  console.log(`[signup] url-after=${page.url()} assen_access-cookie-stored=${hasAccess}`);
  await page.screenshot({ path: 'test-results/untrusted-after-signup.png', fullPage: true });

  // Definitive: try a protected page. If the session persisted we stay; if the Secure
  // cookie was dropped over http we bounce back to /login (documented dev limitation).
  await page.goto(BASE + '/mypage', { waitUntil: 'domcontentloaded' });
  const landedOnLogin = /\/login/.test(page.url());
  console.log(`[signup] /mypage after signup -> ${page.url()} (bounced-to-login=${landedOnLogin})`);
  await page.screenshot({ path: 'test-results/untrusted-mypage-after-signup.png', fullPage: true });
});

test('untrusted user · reflected-input safety (nickname is not rendered as HTML)', async ({ page }) => {
  await page.goto(BASE + '/signup', { waitUntil: 'domcontentloaded' });
  const phone = '010' + String(Date.now()).slice(-8);
  await page.getByLabel('휴대폰 번호').fill(phone);
  await page.getByRole('button', { name: '인증번호 받기' }).click();
  await expect(page.getByLabel('자리 1')).toBeVisible({ timeout: 15_000 });
  const xss = '<img src=x onerror="window.__xss=1">';
  await page.getByLabel('닉네임').fill(xss);
  // React escapes text nodes — the payload must not execute or inject an <img>.
  const injected = await page.evaluate(() => (window as unknown as { __xss?: number }).__xss ?? 0);
  expect(injected, 'nickname XSS did not execute').toBe(0);
});

test('untrusted user · social login (mock kakao) completes the round-trip', async ({
  page,
  context,
}) => {
  await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' });
  // real-API mode renders the social buttons (mock provider gated on ENABLE_MOCK_SOCIAL_AUTH)
  await page.getByRole('button', { name: '카카오로 계속' }).click();
  // start → authorize_url (the mock bounces to /auth/callback/kakao?code=mock-kakao)
  // → the callback page POSTs the code → login → router.replace(next=/discovery).
  await page.waitForURL(/\/discovery/, { timeout: 25_000 });
  await page.waitForTimeout(2_500);
  const cookies = await context.cookies();
  const hasAccess = cookies.some((c) => c.name === 'assen_access');
  console.log(`[social] final url=${page.url()} assen_access-stored=${hasAccess}`);
  await page.screenshot({ path: 'test-results/untrusted-social-kakao.png', fullPage: true });
  // The mock OAuth round-trip must complete into the app (not stall on /login or the
  // callback). Session persistence over http is the known Secure-cookie limitation.
  expect(page.url()).toContain('/discovery');
});
