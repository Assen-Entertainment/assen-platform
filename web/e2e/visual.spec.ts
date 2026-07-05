import { test, expect, type Page, type Locator } from "@playwright/test";
import { otpFor } from "./helpers/otp";

/**
 * 시각 회귀 — 핵심 화면 × 라이트/다크 픽셀 diff(toHaveScreenshot).
 *
 * 결정성: seed_demo의 고정 데이터를 익명으로 읽는다(visual 프로젝트가 저니보다 먼저 실행 —
 * playwright.config 참조). 동적 요소(상대 시간 라벨 `<time>`)는 mask로 가린다. 애니메이션은
 * reducedMotion + animations:"disabled"로 무력화해 재실행 안정성을 확보한다.
 *
 * 베이스라인 생성/갱신: `npx playwright test --project=visual --update-snapshots`
 * (신선한 시드에서 실행 — 커밋에 포함).
 */

const CREATOR_PHONE = "010-0000-0002"; // seed_demo 데모크리에이터 = stellar 오너 → /studio 렌더.

const THEMES = ["light", "dark"] as const;

/**
 * 익명 공개 화면(auth 불요) — 시드 데이터 결정적.
 * ※상품 상세는 라이브에서 상품 id가 서버 UUID라 직접 경로 하드코딩 불가 →
 *   /store에서 첫 카드를 클릭해 진입(아래 별도 테스트). 스크린샷 이름은 고정.
 */
const PUBLIC_SCREENS = [
  { name: "login", path: "/login" },
  { name: "discovery", path: "/discovery" },
  { name: "feed", path: "/feed" },
  { name: "creator-profile", path: "/creator/stellar" },
  { name: "store", path: "/store" },
  { name: "membership", path: "/membership" },
] as const;

/**
 * 매 실행(벽시계) 변동하는 상대 시간 라벨을 가린다. 없는 페이지에선 매칭 0으로 무시된다.
 *  - <time> 엘리먼트(TimeLabel)
 *  - PostCard meta 등 상대 시간이 <time> 밖 텍스트("@handle · 3분 전")로 렌더되는 경우
 *    (index.ts relativeTime — 방금/N분·시간·일 전).
 */
function dynamicMasks(page: Page): Locator[] {
  // 주/개월 형태도 포함 — 오래된 시드 DB 로 재실행하면 "3일 전"이 "N주 전"·"N개월 전"으로 드리프트한다.
  return [page.locator("time"), page.getByText(/방금|\d+분 전|\d+시간 전|\d+일 전|\d+주 전|\d+개월 전/)];
}

async function loginAsCreator(page: Page): Promise<void> {
  await page.goto("/login", { waitUntil: "networkidle" });
  await page.getByLabel("휴대폰 번호").fill(CREATOR_PHONE.replace(/\D/g, ""));
  await page.getByRole("button", { name: "인증번호 받기" }).click();
  await page.getByRole("group", { name: "인증 코드" }).waitFor({ timeout: 10_000 });
  await page.getByLabel("자리 1").click();
  await page.keyboard.type(otpFor(CREATOR_PHONE), { delay: 80 });
  await page.getByRole("button", { name: "로그인" }).click({ timeout: 5_000 });
  await page.waitForURL("**/discovery", { timeout: 25_000 });
}

for (const theme of THEMES) {
  test.describe(`시각 회귀 (${theme})`, () => {
    // 테마는 localStorage("theme")로 주입(FOUC 스크립트가 하이드레이션 전 적용). colorScheme는 보조.
    // reducedMotion은 contextOptions로 전달(1.61 test use는 최상위 reducedMotion을 노출하지 않음).
    test.use({ colorScheme: theme, contextOptions: { reducedMotion: "reduce" } });

    for (const screen of PUBLIC_SCREENS) {
      test(`${screen.name} — ${theme}`, async ({ page, context }) => {
        await context.addInitScript((t) => localStorage.setItem("theme", t), theme);
        await page.goto(screen.path, { waitUntil: "networkidle" });
        // 폰트/레이아웃 settle 여유(reducedMotion으로 애니메이션은 이미 무력).
        await page.waitForTimeout(300);
        await expect(page).toHaveScreenshot(`${screen.name}--${theme}.png`, {
          animations: "disabled",
          mask: dynamicMasks(page),
        });
      });
    }

    test(`product-detail — ${theme}`, async ({ page, context }) => {
      await context.addInitScript((t) => localStorage.setItem("theme", t), theme);
      // 라이브 상품 id는 UUID(카드는 router.push로 이동 — 앵커 없음) → API로 첫 상품 id를 받아
      // 상세로 직행한다. 첫 상품은 시드 순서로 결정적이고, 스크린샷 이름은 고정.
      const res = await page.request.get("/api/products");
      const body = await res.json();
      const first = (body.items ?? body)[0];
      await page.goto(`/store/${first.id}`, { waitUntil: "networkidle" });
      await page.waitForTimeout(300);
      await expect(page).toHaveScreenshot(`product-detail--${theme}.png`, {
        animations: "disabled",
        mask: dynamicMasks(page),
      });
    });

    test(`studio-dashboard — ${theme}`, async ({ page, context }) => {
      await context.addInitScript((t) => localStorage.setItem("theme", t), theme);
      await loginAsCreator(page);
      await page.goto("/studio", { waitUntil: "networkidle" });
      await page.waitForTimeout(300);
      await expect(page).toHaveScreenshot(`studio-dashboard--${theme}.png`, {
        animations: "disabled",
        mask: dynamicMasks(page),
      });
    });
  });
}
