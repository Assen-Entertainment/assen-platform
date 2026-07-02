import { expect, type Page, test } from '@playwright/test';

// Web/UI E2E for the fan app's Slice 4 My hub (ASS-147): the account hub becomes
// an inline list-detail at QHD. Pane geometry is asserted by the widget tests
// (my_list_detail_test, points_history_dense_list_test); here we confirm the My
// hub boots after sign-in and fills the QHD width with a menu + detail pane
// (screenshot captured for visual verdict).

const WEB = process.env.WEB_BASE_URL ?? 'http://127.0.0.1:8080';
const APP = `${WEB}/app/`;

async function waitForFlutter(page: Page): Promise<void> {
  await page.waitForSelector('flutter-view, flt-glass-pane', { timeout: 60_000 });
  await page.waitForTimeout(1_500);
}

async function enableSemantics(page: Page): Promise<void> {
  const placeholder = page
    .locator('flt-semantics-placeholder, [aria-label="Enable accessibility"]')
    .first();
  await placeholder.waitFor({ state: 'attached', timeout: 15_000 });
  await placeholder.evaluate((el) => (el as HTMLElement).click());
  await page.waitForSelector('input[aria-label="아이디"]', { timeout: 15_000 });
}

async function signIn(page: Page): Promise<void> {
  const password = page.locator('input[aria-label="비밀번호"]');
  await password.waitFor({ state: 'attached', timeout: 15_000 });
  const box = await password.boundingBox();
  expect(box, 'password input bounding box').not.toBeNull();
  await page.mouse.click(box!.x + box!.width / 2, box!.y + box!.height + 56);
  await page.waitForURL(/#\/home/, { timeout: 15_000 });
  await page.waitForTimeout(1_500);
}

async function goHash(page: Page, hash: string): Promise<void> {
  await page.evaluate((h) => {
    window.location.hash = h;
  }, hash);
  await page.waitForURL(new RegExp(hash.replace('/', '\\/')), { timeout: 15_000 });
  await page.waitForTimeout(1_500);
}

test.describe('fan app Slice 4 My hub (web)', () => {
  test('QHD My hub renders the menu beside the points detail', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 2560, height: 1440 });
    await page.goto(APP);
    await waitForFlutter(page);
    await enableSemantics(page);
    await signIn(page);

    await goHash(page, '#/my/points');

    await expect(page.locator('flutter-view, flt-glass-pane').first()).toBeVisible();
    // Visual verdict artifact: sidebar + a fixed account menu pane + the points
    // ledger filling the detail pane across the full QHD width.
    await page.screenshot({
      path: 'test-results/fan-my-hub-qhd-2560.png',
      fullPage: false,
    });
  });
});
