import { expect, type Page } from "@playwright/test";

/**
 * 이메일/비밀번호 로그인 헬퍼(B1: 폰 OTP 로그인 대체).
 *
 * 서버 seed_demo가 데모 팬·크리에이터 계정에 **인증 완료된** 이메일 크리덴셜을 심어두므로
 * (email + password_hash + email_verified_at), E2E는 POST /fan/login/email로 결정적으로 로그인한다.
 * 자격은 seed_demo.py의 _DEMO_FAN_EMAIL/_DEMO_CREATOR_EMAIL/_DEMO_PASSWORD와 동기 — 서버가 바뀌면
 * 여기도 함께 바꿔야 저니가 통과한다.
 */
export const DEMO_FAN_EMAIL = "demo-fan@assen.test";
export const DEMO_CREATOR_EMAIL = "demo-creator@assen.test";
export const DEMO_PASSWORD = "assen-demo-pass";

/**
 * /login으로 이동해 이메일·비밀번호를 라벨로 채우고 로그인한 뒤, 로그인 성공 착지(/discovery)를 대기한다.
 */
export async function loginViaEmail(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login", { waitUntil: "networkidle" });
  const emailField = page.getByLabel("이메일");
  await expect(emailField, "이메일 로그인 폼(live 모드) 렌더").toBeVisible();
  await emailField.fill(email);
  await page.getByLabel("비밀번호").fill(password);
  await page.getByRole("button", { name: "로그인" }).click();
  await page.waitForURL("**/discovery", { timeout: 25_000 });
}
