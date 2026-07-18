import { test, expect } from '@playwright/test';
import { BASE, socialLogin, ensureKyc } from './_dev-e2e-helpers';

/**
 * Full FAN journey against dev over https: login → KYC → discover a creator → follow →
 * subscribe to a paid tier (mock payment) → buy a digital product (mock payment) → confirm
 * both in /mypage/subscriptions and /orders.
 *
 * Consumes content seeded on the deterministic google-creator `e2ecreator` (a selling
 * DIGITAL product + an active paid tier). Digital, not goods: demo has
 * shipping_checkout_available=false, so a goods checkout is blocked by design.
 *
 * The fan account = mock KAKAO (distinct from the google creator). Writes (follow /
 * subscribe / order) are throttled (FAN_WRITE_THROTTLE, per-minute) — run once.
 */
const CREATOR = 'e2ecreator';

test('dev fan · follow → subscribe → buy, end to end', async ({ page }) => {
  test.setTimeout(120_000);

  // naver = a clean fan (the kakao account is already dirtied by the API-level E2E). This
  // also exercises the real KYC UI (naver starts unverified) rather than the skip path.
  await test.step('login (naver) + KYC', async () => {
    await socialLogin(page, 'naver');
    await ensureKyc(page);
  });

  await test.step('open the creator and FOLLOW', async () => {
    await page.goto(`${BASE}/creator/${CREATOR}`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('E2E Seed Creator').first()).toBeVisible({ timeout: 15_000 });
    const followBtn = page.getByRole('button', { name: '팔로우' });
    if (await followBtn.isVisible().catch(() => false)) {
      await followBtn.click();
    }
    // idempotent: whether we just followed or were already following, the state is 팔로잉.
    await expect(page.getByRole('button', { name: '팔로잉' })).toBeVisible({ timeout: 15_000 });
  });

  await test.step('SUBSCRIBE to the paid tier (mock payment)', async () => {
    await page.goto(`${BASE}/creator/${CREATOR}`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('tab', { name: '멤버십' }).click();
    // Fresh fan → CTA is 구독하기; already-subscribed → 구독 중 (disabled). Wait for whichever.
    const subscribeBtn = page.getByRole('button', { name: '구독하기' }).first();
    const alreadyBtn = page.getByRole('button', { name: '구독 중' }).first();
    await expect(subscribeBtn.or(alreadyBtn)).toBeVisible({ timeout: 15_000 });
    if (await subscribeBtn.isVisible().catch(() => false)) {
      await subscribeBtn.click();
      await page.waitForURL(/\/checkout/, { timeout: 15_000 });
      await page.locator('#checkout-agree').click();
      await page.locator('#autopay-consent').click();
      await page.getByRole('button', { name: /결제하기/ }).first().click();
      await page.waitForURL(/\/mypage\/subscriptions/, { timeout: 20_000 });
    }
    // Confirm the active subscription regardless of path.
    await page.goto(`${BASE}/mypage/subscriptions`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('구독 중').first()).toBeVisible({ timeout: 15_000 });
  });

  await test.step('BUY the digital product (mock payment)', async () => {
    await page.goto(`${BASE}/store`, { waitUntil: 'domcontentloaded' });
    // open the seeded digital product from the store list (card → /store/{id}).
    const card = page.locator('a[href^="/store/"]', { hasText: 'E2E 디지털 상품' }).first();
    if (await card.isVisible().catch(() => false)) {
      await card.click();
    } else {
      // fallback: the card's 구매 button navigates to the detail
      await page
        .locator(':has-text("E2E 디지털 상품")')
        .getByRole('button', { name: '구매' })
        .first()
        .click();
    }
    await page.waitForURL(/\/store\/[^/]+$/, { timeout: 15_000 });
    // detail CTA is rendered twice (desktop + mobile) — take the first.
    await page.getByRole('button', { name: '구매하기' }).first().click();
    await page.waitForURL(/\/checkout/, { timeout: 15_000 });
    // digital → no shipping form; card is the default method.
    await page.locator('#checkout-agree').click();
    await page.getByRole('button', { name: /결제하기/ }).first().click();
    await page.waitForURL(/\/checkout\/complete/, { timeout: 20_000 });
    await expect(page.getByText('주문이 완료됐어요!')).toBeVisible({ timeout: 15_000 });
  });

  await test.step('order appears in /orders as 결제완료', async () => {
    await page.goto(`${BASE}/orders`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('결제완료').first()).toBeVisible({ timeout: 15_000 });
  });
});
