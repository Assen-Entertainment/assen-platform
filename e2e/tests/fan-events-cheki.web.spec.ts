import { expect, type Page, test } from '@playwright/test';

// Web/UI E2E for the fan app's Slice 3 desktop surfaces (ASS-147): the events
// list-detail and the cheki feed at QHD. Flutter web paints to a canvas, so the
// pane geometry / column counts are asserted deterministically by the widget
// tests (events_list_detail_test, events_pane_embed_test,
// list_detail_branch_reset_test, cheki_album_grid_extended_test,
// list_detail_scaffold_test). Here we cover what only a real browser shows:
// the events and cheki surfaces boot after sign-in and fill the QHD width
// (screenshots captured for visual verdict).
//
// Run (web suite is separate from the default API config — see README):
//   WEB_BASE_URL=http://127.0.0.1:8080 npm run test:web

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

test.describe('fan app Slice 3 desktop surfaces (web)', () => {
  test('QHD events list-detail fills the width after sign-in', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 2560, height: 1440 });
    await page.goto(APP);
    await waitForFlutter(page);
    await enableSemantics(page);
    await signIn(page);

    await goHash(page, '#/events');

    await expect(page.locator('flutter-view, flt-glass-pane').first()).toBeVisible();
    // Best-effort: click into the list pane to populate the detail pane (canvas
    // hit; the screenshot is valid either way — prompt or selected detail).
    await page.mouse.click(360, 340);
    await page.waitForTimeout(800);
    // Visual verdict artifact: event feed (left) beside the detail pane (right)
    // spanning the full QHD width — no centered reading column / right gutter.
    await page.screenshot({
      path: 'test-results/fan-events-qhd-2560.png',
      fullPage: false,
    });
  });

  test('QHD cheki album fills the width with a dense grid', async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1440 });
    await page.goto(APP);
    await waitForFlutter(page);
    await enableSemantics(page);
    await signIn(page);

    await goHash(page, '#/cheki');

    await expect(page.locator('flutter-view, flt-glass-pane').first()).toBeVisible();
    // Visual verdict artifact: 5-6 cheki frames per row filling the sidebar-shell
    // body (geometry pinned by cheki_album_grid_extended_test).
    await page.screenshot({
      path: 'test-results/fan-cheki-qhd-2560.png',
      fullPage: false,
    });
  });
});
