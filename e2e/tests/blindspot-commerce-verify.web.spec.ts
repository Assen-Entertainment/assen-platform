import { test, expect } from '@playwright/test';

// Verifies the sold-out CTA blindspot fixes (store card + product detail).
// A seeded goods product with stock=0 ("한정판 피규어") must surface a proper
// disabled "품절" CTA — never the shipping-gate "배송 결제 준비 중이에요" or an
// enabled buy button. Public pages, no auth needed.
//   WEB_BASE_URL=http://localhost:3000 npx playwright test tests/blindspot-commerce-verify.web.spec.ts --config playwright.web.config.ts
const BASE = process.env.WEB_BASE_URL ?? 'http://localhost:3000';
// Deterministic (uuid5) seed id of the stock=0 goods product.
const SOLD_OUT_ID = '969a5c26-6a7a-5fe8-bde6-5363d1da610e';

test('product detail · sold-out shows disabled 품절 CTA (not shipping-gate)', async ({ page }) => {
  await page.goto(`${BASE}/store/${SOLD_OUT_ID}`, { waitUntil: 'networkidle' });
  const cta = page.getByRole('button', { name: '품절', exact: true }).first();
  await expect(cta).toBeVisible();
  await expect(cta).toBeDisabled();
  // sold-out must take precedence over the goods shipping gate
  await expect(page.getByText('배송 결제 준비 중이에요')).toHaveCount(0);
});

test('store page · sold-out card surfaces 품절', async ({ page }) => {
  await page.goto(`${BASE}/store`, { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'test-results/blindspot/store-soldout.png', fullPage: true });
  await expect(page.getByText('품절').first()).toBeVisible();
});

test('store filter · category narrows with no empty+load-more contradiction', async ({ page }) => {
  await page.goto(`${BASE}/store`, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '디지털', exact: true }).click();
  await page.waitForTimeout(700);
  await page.screenshot({ path: 'test-results/blindspot/store-filter-digital.png', fullPage: true });
  // digital is seeded → not empty; and while filtering the manual "더 보기" must be hidden
  // (auto-load handles pagination) — the empty-state + load-more can never coexist.
  await expect(page.getByText('상품이 없어요')).toHaveCount(0);
  await expect(page.getByRole('button', { name: '더 보기' })).toHaveCount(0);
});
