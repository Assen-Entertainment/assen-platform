import { test, expect } from '@playwright/test';

// Payoff check for the dev HTTPS work (dev.assenent.com + ACM): with the site now served
// over https, the Secure auth cookies (assen_access, assen_social_state) persist in a real
// browser, so self-service authentication — impossible over http — now completes end to end.
//   WEB_BASE_URL=https://dev.assenent.com npx playwright test tests/dev-https-auth.web.spec.ts --config playwright.web.config.ts
const BASE = process.env.WEB_BASE_URL ?? 'https://dev.assenent.com';

test('dev https · mock social login completes AND the Secure session persists', async ({ page, context }) => {
  test.setTimeout(60_000);
  await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: '카카오로 계속하기' }).click();

  // mock OAuth: start -> /auth/callback/kakao?code=mock-kakao -> callback POST -> /discovery
  await page.waitForURL(/\/discovery/, { timeout: 30_000 });

  const access = (await context.cookies()).find((c) => c.name === 'assen_access');
  expect(access, 'assen_access cookie is set after social login').toBeTruthy();
  expect(access?.secure, 'the session cookie is Secure').toBe(true);

  // Definitive: a protected page must NOT bounce to /login now that the Secure cookie
  // survives over https (the exact check that failed over http — the whole point of HTTPS).
  await page.goto(BASE + '/mypage', { waitUntil: 'domcontentloaded' });
  await expect(page, 'protected page stays (session persisted)').not.toHaveURL(/\/login/, { timeout: 15_000 });
  expect(new URL(page.url()).pathname).toContain('/mypage');
});
