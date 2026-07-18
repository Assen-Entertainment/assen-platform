import { test, expect } from '@playwright/test';
import {
  BASE,
  USE_EMAIL_AUTH,
  socialLogin,
  bootstrapEmailCreator,
  ensureCreator,
} from './_dev-e2e-helpers';

/**
 * Full CREATOR content-creation journey against dev over https: login → (KYC-gated)
 * become-creator → studio → create a product → create a membership tier → publish a post,
 * each asserted by the durable result (the new row/card/navigation) rather than a toast
 * (toasts race the follow-up navigation and are flaky).
 *
 * Deployed dev → a fresh email-verified account promoted to a creator with a unique handle
 * (bootstrapEmailCreator clears the KYC gate first). Local mock stack → the mock GOOGLE
 * account, which the seed already made the creator `e2ecreator` (KYC-verified); ensureCreator
 * is idempotent and lands straight on /studio. Writes are throttled (FAN_WRITE_THROTTLE,
 * per-minute) — run once.
 *
 * NOTE: becoming a creator requires KYC server-side (403 IdentityVerificationRequired
 * otherwise); the mock verifier passes on demo.
 */
const STAMP = String(Date.now()).slice(-6);
// Deployed dev needs a unique handle (a fresh account cannot claim the seeded `e2ecreator`).
const HANDLE = USE_EMAIL_AUTH ? `e2ecr${STAMP}` : 'e2ecreator';
const CREATOR_NAME = 'E2E Seed Creator';

test('dev creator · become-creator → create product, tier, post', async ({ page }) => {
  test.setTimeout(120_000);

  await test.step('login + reach studio as a creator', async () => {
    if (USE_EMAIL_AUTH) {
      await bootstrapEmailCreator(page, HANDLE, CREATOR_NAME);
    } else {
      await socialLogin(page, 'google');
      await ensureCreator(page, HANDLE, CREATOR_NAME);
    }
    await page.goto(`${BASE}/studio`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: '크리에이터 스튜디오' })).toBeVisible({ timeout: 15_000 });
  });

  await test.step('create a product', async () => {
    const title = `스튜디오 E2E 상품 ${STAMP}`;
    await page.goto(`${BASE}/studio/products`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: '새 상품' }).click();
    await expect(page.getByText('새 상품 등록')).toBeVisible({ timeout: 10_000 });
    await page.getByLabel('상품명').fill(title);
    await page.getByLabel('가격 (원)').fill('12000');
    await page.getByRole('button', { name: '등록' }).click();
    // durable: the new row shows up in the 상품 목록.
    await expect(page.getByText(title).first()).toBeVisible({ timeout: 15_000 });
  });

  await test.step('create a membership tier', async () => {
    const name = `E2E 티어 ${STAMP}`;
    await page.goto(`${BASE}/studio/membership`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: '새 티어' }).click();
    await expect(page.getByText('새 티어 만들기')).toBeVisible({ timeout: 10_000 });
    await page.getByLabel('티어 이름').fill(name);
    await page.getByLabel('월 가격 (원)').fill('4000');
    await page.getByLabel('혜택 (한 줄에 하나씩)').fill('독점 콘텐츠\n한정 배지');
    await page.getByRole('button', { name: '만들기' }).click();
    // durable: the new tier card appears.
    await expect(page.getByText(name).first()).toBeVisible({ timeout: 15_000 });
  });

  await test.step('publish a post', async () => {
    await page.goto(`${BASE}/studio/posts/new`, { waitUntil: 'domcontentloaded' });
    await page.getByLabel('제목').fill(`E2E 포스트 ${STAMP}`);
    await page.getByLabel('본문').fill('스튜디오 E2E로 발행한 본문입니다.');
    await page.getByRole('button', { name: '발행하기' }).click();
    // durable: publish navigates back to /studio.
    await page.waitForURL(/\/studio(\?|$|\/)/, { timeout: 20_000 });
    await expect(page).not.toHaveURL(/\/posts\/new/);
  });
});
