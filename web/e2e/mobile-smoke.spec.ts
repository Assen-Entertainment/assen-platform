import { test, expect } from "@playwright/test";
import { DEMO_FAN_EMAIL, DEMO_PASSWORD, loginViaEmail } from "./helpers/auth";

/**
 * 모바일 스모크 서브셋(375) — 로그인·디스커버리·피드.
 * 좁은 뷰포트에서 핵심 진입 동선(이메일 로그인 → 반응형 셸 → 피드)이 렌더/동작하는지만 확인.
 * 전체 커머스 저니는 데스크톱 journey.spec가 담당(중복 회피).
 */

test("모바일 — 이메일 로그인 → 디스커버리 → 피드", async ({ page }) => {
  await test.step("이메일 로그인 → 디스커버리 진입", async () => {
    await loginViaEmail(page, DEMO_FAN_EMAIL, DEMO_PASSWORD);
    // 로그인 성공 착지 = 디스커버리. 콘텐츠(크리에이터 카드 등)가 최소 1개 렌더.
    await expect(page.getByRole("link", { name: /별빛|Neon|토끼|묘화/ }).first()).toBeVisible({ timeout: 10_000 });
  });

  await test.step("하단 탭 셸(모바일) 노출", async () => {
    // 375 뷰포트에서 반응형 셸의 하단 내비게이션이 렌더된다.
    await expect(page.getByRole("navigation").first()).toBeVisible();
  });

  await test.step("피드 렌더", async () => {
    await page.goto("/feed", { waitUntil: "networkidle" });
    // 피드 포스트(article)가 최소 1개 렌더되고 포스트 상세 링크를 가진다.
    await expect(page.locator("article a[href^='/post/']").first()).toBeVisible({ timeout: 10_000 });
  });
});
