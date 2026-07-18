import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';

// Verifies the two blindspot fixes found by the audit:
//   1) /studio is gated to creators — a non-creator (phone signup) is redirected to /become-creator.
//   2) The profile dropdown never shows a raw UUID as "@handle" for a non-creator.
// Run against the running local stack (web :3000 proxying /api → Django :8000):
//   WEB_BASE_URL=http://localhost:3000 npx playwright test tests/blindspot-fix-verify.web.spec.ts --config playwright.web.config.ts
const BASE = process.env.WEB_BASE_URL ?? 'http://localhost:3000';

function otpFor(phone: string): string {
  const hex = crypto.createHmac('sha256', 'assen-dev-otp').update(phone, 'utf8').digest('hex');
  return String(parseInt(hex.slice(0, 8), 16) % 1_000_000).padStart(6, '0');
}
function normalizePhone(phone: string): string {
  const d = phone.replace(/\D/g, '');
  return d.startsWith('0') ? '+82' + d.slice(1) : '+' + d;
}

// Establish a fan (non-creator) session via the API so navigation is authenticated
// without flaky UI clicks. Returns the phone used.
async function signupFan(page: import('@playwright/test').Page): Promise<string> {
  const phone = '010' + String(Date.now()).slice(-8);
  const code = otpFor(normalizePhone(phone));
  await page.request.post(BASE + '/api/fan/signup/otp', { data: { phone } });
  const res = await page.request.post(BASE + '/api/fan/signup', {
    data: { phone, otp_code: code, nickname: '게이트검증팬', consent_terms: true, consent_privacy: true, age_over_14: true, web: true },
  });
  expect(res.ok(), 'fan signup via api').toBeTruthy();
  return phone;
}

test('studio gate · non-creator is redirected to become-creator', async ({ page }) => {
  test.setTimeout(60_000);
  await signupFan(page);
  await page.goto(BASE + '/studio', { waitUntil: 'domcontentloaded' });
  // client-side gate redirects; wait for the URL to settle on become-creator
  await page.waitForURL(/\/become-creator/, { timeout: 15_000 });
  expect(page.url()).toContain('/become-creator');
  // the non-creator affordance ("크리에이터 되기") is shown; studio dashboard is not.
  await expect(page.getByText('크리에이터 되기', { exact: false }).first()).toBeVisible();
});

test('profile dropdown · no raw UUID handle for non-creator', async ({ page }) => {
  test.setTimeout(60_000);
  await signupFan(page);
  await page.goto(BASE + '/discovery', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '내 계정 메뉴' }).click();
  await page.waitForTimeout(500);
  // whole rendered page (incl. open dropdown) must not surface an @<uuid> anywhere
  const body = (await page.locator('body').textContent()) ?? '';
  expect(body).not.toMatch(/@[0-9a-f]{8}-[0-9a-f]{4}-/i);
});
