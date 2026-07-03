/**
 * 시각 스모크 — 주요 라우트 × 뷰포트 × 테마 스크린샷 + 콘솔 에러 수집.
 * 사용: node scripts/visual-smoke.mjs [baseUrl] (기본 http://localhost:3000, dev/start 서버 선행)
 * 산출: .smoke/ 아래 PNG + report.json (콘솔 에러·페이지 에러·404 응답 요약)
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const BASE = process.argv[2] ?? "http://localhost:3000";
const OUT = join(process.cwd(), ".smoke");

const ROUTES = [
  "/discovery",
  "/feed",
  "/search?q=%EC%8A%A4%ED%85%94%EB%9D%BC",
  "/creator/stellar",
  "/creator/stellar/followers",
  "/post/po1",
  "/store",
  "/store/p1",
  "/store/p8",
  "/store/p9",
  "/membership",
  "/mypage",
  "/mypage/subscriptions",
  "/notifications",
  "/orders",
  "/orders/ASN-1024",
  "/studio",
  "/studio/posts/new",
  "/studio/products",
  "/studio/membership",
  "/studio/settlement",
  "/studio/analytics",
  "/settings",
  "/settings/account",
  "/settings/notifications",
  "/settings/payments",
  "/login",
  "/signup",
  "/forgot-password",
  "/policy/terms",
  "/checkout?item=p1",
  "/checkout/complete?order=ASN-TEST",
  "/403",
  "/session-expired",
];

const VIEWPORTS = [
  { name: "375", width: 375, height: 812 },
  { name: "768", width: 768, height: 1024 },
  { name: "1280", width: 1280, height: 800 },
  { name: "1536", width: 1536, height: 960 },
];

const THEMES = ["light", "dark"];

const slug = (r) => r.replace(/[/?=&%]+/g, "_").replace(/^_|_$/g, "") || "home";

async function main() {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const report = [];

  for (const theme of THEMES) {
    for (const vp of VIEWPORTS) {
      const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      // FOUC 스크립트보다 먼저 localStorage 주입
      await ctx.addInitScript((t) => localStorage.setItem("theme", t), theme);
      const page = await ctx.newPage();
      const consoleErrors = [];
      page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));
      page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));

      for (const route of ROUTES) {
        const errsBefore = consoleErrors.length;
        let status = null;
        try {
          const res = await page.goto(BASE + route, { waitUntil: "networkidle", timeout: 30000 });
          status = res?.status() ?? null;
          await page.waitForTimeout(300);
          // 가로 스크롤(레이아웃 붕괴) 감지
          const hasHScroll = await page.evaluate(
            () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
          );
          await page.screenshot({
            path: join(OUT, `${slug(route)}--${vp.name}--${theme}.png`),
            fullPage: false,
          });
          report.push({
            route,
            viewport: vp.name,
            theme,
            status,
            hScroll: hasHScroll,
            consoleErrors: consoleErrors.slice(errsBefore),
          });
        } catch (e) {
          report.push({ route, viewport: vp.name, theme, status, error: String(e).slice(0, 200) });
        }
      }
      await ctx.close();
    }
  }
  await browser.close();

  const bad = report.filter(
    (r) => r.error || (r.status && r.status >= 400) || r.hScroll || (r.consoleErrors?.length ?? 0) > 0,
  );
  writeFileSync(join(OUT, "report.json"), JSON.stringify({ base: BASE, total: report.length, bad, report }, null, 2));
  console.log(`smoke done: ${report.length} shots, ${bad.length} issues -> .smoke/report.json`);
  process.exitCode = bad.length > 0 ? 1 : 0;
}

main();
