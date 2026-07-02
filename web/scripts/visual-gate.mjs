// Assen DS 시각 게이트 — /gallery 라이트·다크·모바일 풀페이지 스크린샷.
// WSL 실행: pnpm add -D playwright && npx playwright install chromium && node scripts/visual-gate.mjs
// (dev 서버가 떠 있어야 함: pnpm dev)
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const BASE = process.env.BASE_URL || "http://localhost:3000";
const OUT = ".screenshots";

async function shoot(page, name) {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  console.log("saved", `${OUT}/${name}.png`);
}

const browser = await chromium.launch();
try {
  await mkdir(OUT, { recursive: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 2000 }, deviceScaleFactor: 2 });
  await page.goto(`${BASE}/gallery`, { waitUntil: "load" });
  await page.waitForTimeout(300);
  await shoot(page, "gallery-light");

  // 헤더의 다크 토글 클릭
  await page.getByRole("button", { name: /다크|라이트/ }).click();
  await page.waitForTimeout(300);
  await shoot(page, "gallery-dark");

  // 서비스 플로우 화면 (라이트)
  for (const route of [
    "/discovery", "/creator", "/store", "/checkout", "/checkout/complete",
    "/feed", "/search", "/post", "/mypage", "/notifications", "/orders", "/studio",
    "/onboarding", "/login", "/signup", "/age-gate",
  ]) {
    await page.setViewportSize({ width: 1280, height: 2000 });
    await page.goto(`${BASE}${route}`, { waitUntil: "load" });
    await page.waitForTimeout(300);
    await shoot(page, "screen" + route.replace(/\//g, "-"));
  }

  // 모바일 폭 재촬영(갤러리)
  await page.goto(`${BASE}/gallery`, { waitUntil: "load" });
  await page.setViewportSize({ width: 390, height: 2600 });
  await page.waitForTimeout(200);
  await shoot(page, "gallery-mobile");
} finally {
  await browser.close();
}
