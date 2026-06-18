import { expect, type Page, test } from '@playwright/test';

// Web/UI E2E for the fan app's adaptive shell (ASS-147 desktop optimization).
//
// Unlike the API specs in this folder, this drives the composed local web shell
// (scripts/build-web-local.sh -> serve-web-local.sh, default :8080). Flutter web
// paints its widgets to a canvas, so the home's feed/stack geometry is asserted
// deterministically by the fan_app widget tests (home_dashboard_layout_test,
// home_supporting_pane_layout_test, home_sidebar_budget_test) and
// sidebar_shell_test. Here we cover what only a real browser shows: the login
// form's IME input proxies are width-capped (not edge-to-edge) on a wide
// viewport, sign-in works (hash route advances to /home), and screenshots of
// the desktop (sidebar + feed + membership rail), QHD, and mobile (stacked)
// home are captured for visual verdict.
//
// Run (web suite is separate from the default API config — see README):
//   WEB_BASE_URL=http://127.0.0.1:8080 npm run test:web
// Default base URL matches scripts/serve-web-local.sh (WEB_PORT defaults 8080).

const WEB = process.env.WEB_BASE_URL ?? 'http://127.0.0.1:8080';
const APP = `${WEB}/app/`;

async function waitForFlutter(page: Page): Promise<void> {
  await page.waitForSelector('flutter-view, flt-glass-pane', { timeout: 60_000 });
  await page.waitForTimeout(1_500);
}

// Flutter only attaches the per-field DOM <input> IME proxies (which carry the
// aria-labels we assert on and anchor to) once accessibility is enabled. The
// "Enable accessibility" placeholder is positioned off-screen, so a normal
// actionable click fails — dispatch the click through the DOM instead.
async function enableSemantics(page: Page): Promise<void> {
  const placeholder = page
    .locator('flt-semantics-placeholder, [aria-label="Enable accessibility"]')
    .first();
  await placeholder.waitFor({ state: 'attached', timeout: 15_000 });
  await placeholder.evaluate((el) => (el as HTMLElement).click());
  await page.waitForSelector('input[aria-label="아이디"]', { timeout: 15_000 });
}

// The login fields are decorative (the P3a stub signs in with fixed mock
// credentials); the login button is canvas-painted just below the password
// field, so click it by coordinate anchored to that field's DOM box. Sign-in
// drives the hash router to /home.
async function signIn(page: Page): Promise<void> {
  const password = page.locator('input[aria-label="비밀번호"]');
  await password.waitFor({ state: 'attached', timeout: 15_000 });
  const box = await password.boundingBox();
  expect(box, 'password input bounding box').not.toBeNull();
  await page.mouse.click(box!.x + box!.width / 2, box!.y + box!.height + 56);
  await page.waitForURL(/#\/home/, { timeout: 15_000 });
  await page.waitForTimeout(1_500);
}

test.describe('fan app adaptive shell (web)', () => {
  test('login form is width-capped on a wide desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 900 });
    await page.goto(APP);
    await waitForFlutter(page);
    await enableSemantics(page);

    const id = page.locator('input[aria-label="아이디"]');
    const box = await id.boundingBox();
    expect(box, 'id input bounding box').not.toBeNull();

    // Capped near AssenLayout.formMaxWidth (420) rather than stretching across
    // the 1600px viewport.
    expect(box!.width, 'id input not edge-to-edge').toBeLessThanOrEqual(480);

    await page.screenshot({
      path: 'test-results/fan-login-wide-1600.png',
      fullPage: false,
    });
  });

  test('desktop home renders the sidebar + feed + rail after sign-in', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(APP);
    await waitForFlutter(page);
    await enableSemantics(page);
    await signIn(page);

    await expect(page.locator('flutter-view, flt-glass-pane').first()).toBeVisible();
    // Visual verdict artifact (large class): persistent sidebar + a feed of
    // section cards beside the membership rail (geometry asserted by the
    // fan_app widget tests home_supporting_pane_layout_test / sidebar_shell).
    await page.screenshot({
      path: 'test-results/fan-home-desktop-1440.png',
      fullPage: false,
    });
  });

  test('QHD home fills the width with the desktop layout after sign-in', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 2560, height: 1440 });
    await page.goto(APP);
    await waitForFlutter(page);
    await enableSemantics(page);
    await signIn(page);

    await expect(page.locator('flutter-view, flt-glass-pane').first()).toBeVisible();
    // Visual verdict artifact (extra-large/QHD): 256px sidebar + a 3-column feed
    // + membership rail spanning the full width (no centered 1280 reading
    // column / right gutter). This is the user-reported "50% empty" fix.
    await page.screenshot({
      path: 'test-results/fan-home-qhd-2560.png',
      fullPage: false,
    });
  });

  test('mobile home renders the stacked column after sign-in', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(APP);
    await waitForFlutter(page);
    await enableSemantics(page);
    await signIn(page);

    await expect(page.locator('flutter-view, flt-glass-pane').first()).toBeVisible();
    // Visual verdict artifact: the same sections stacked in a single column.
    await page.screenshot({
      path: 'test-results/fan-home-mobile-390.png',
      fullPage: false,
    });
  });
});
