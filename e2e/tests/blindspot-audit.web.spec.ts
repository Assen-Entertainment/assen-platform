import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';

// Blindspot audit: capture the running local app (logged-out + logged-in, desktop +
// mobile) so a human eye can find UX/completeness gaps that functional QA misses
// (missing actions, empty states, inconsistency, responsiveness).
//   WEB_BASE_URL=http://localhost:3000 npx playwright test tests/blindspot-audit.web.spec.ts --config playwright.web.config.ts
const BASE = process.env.WEB_BASE_URL ?? 'http://localhost:3000';

function otpFor(phone: string): string {
  const hex = crypto.createHmac('sha256', 'assen-dev-otp').update(phone, 'utf8').digest('hex');
  return String(parseInt(hex.slice(0, 8), 16) % 1_000_000).padStart(6, '0');
}
function normalizePhone(phone: string): string {
  const d = phone.replace(/\D/g, '');
  return d.startsWith('0') ? '+82' + d.slice(1) : '+' + d;
}

const DESKTOP = { width: 1440, height: 900 };
const MOBILE = { width: 390, height: 844 };

async function capture(page: import('@playwright/test').Page, name: string, path: string) {
  await page.goto(BASE + path, { waitUntil: 'domcontentloaded' }).catch(() => {});
  await page.waitForTimeout(1_200);
  await page.screenshot({ path: `test-results/blindspot/${name}.png`, fullPage: true });
}

test('blindspot · logged-out (desktop)', async ({ page }) => {
  await page.setViewportSize(DESKTOP);
  for (const [n, p] of [['out-discovery', '/discovery'], ['out-login', '/login'], ['out-signup', '/signup'], ['out-store', '/store'], ['out-membership', '/membership']] as const) {
    await capture(page, n, p);
  }
});

test('blindspot · logged-in (desktop)', async ({ page }) => {
  test.setTimeout(120_000);
  await page.setViewportSize(DESKTOP);
  const phone = '010' + String(Date.now()).slice(-8);
  const code = otpFor(normalizePhone(phone));
  // Establish a session via the API (no flaky UI clicks) — the Set-Cookie lands in the
  // browser context, so subsequent page.goto navigations are authenticated.
  await page.request.post(BASE + '/api/fan/signup/otp', { data: { phone } });
  const signup = await page.request.post(BASE + '/api/fan/signup', {
    data: {
      phone,
      otp_code: code,
      nickname: '블라인드테스터',
      consent_terms: true,
      consent_privacy: true,
      age_over_14: true,
      web: true,
    },
  });
  expect(signup.ok(), 'signup via api').toBeTruthy();

  for (const [n, p] of [['in-discovery', '/discovery'], ['in-mypage', '/mypage'], ['in-settings', '/settings'], ['in-notifications', '/notifications'], ['in-orders', '/orders'], ['in-studio', '/studio']] as const) {
    await capture(page, n, p);
  }
  // profile dropdown open (the fix from this session)
  await page.goto(BASE + '/discovery', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '내 계정 메뉴' }).click().catch(() => {});
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'test-results/blindspot/in-profile-dropdown.png' });
});

test('blindspot · mobile', async ({ page }) => {
  await page.setViewportSize(MOBILE);
  for (const [n, p] of [['m-discovery', '/discovery'], ['m-login', '/login'], ['m-store', '/store']] as const) {
    await capture(page, n, p);
  }
});
