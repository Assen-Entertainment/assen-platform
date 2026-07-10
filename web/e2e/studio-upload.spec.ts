import { test, expect, type Page } from "@playwright/test";
import { otpFor } from "./helpers/otp";

/**
 * 스튜디오 포스트 작성 with 이미지 업로드(R12) — 웹(Next, live 모드) + 서버(Django, seed_demo) 결합.
 * 데모 크리에이터(010-0000-0002, stellar 오너)로 로그인 → 작은 PNG를 POST /api/uploads로 업로드 →
 * 반환 media_url을 실은 포스트를 발행 → 스튜디오 포스트 목록 노출 + media_url이 /media/uploads/… 확인.
 *
 * 전제(journey.spec.ts와 동일): Django 127.0.0.1:8000(dev·mock OTP·seed_demo·SERVE_LOCAL_MEDIA on),
 *   Next(NEXT_PUBLIC_API_URL=/api·rewrites)가 playwright.config baseURL로 접근 가능.
 * ※발행은 오너(크리에이터)만 가능하므로 데모팬(0001)이 아닌 데모 크리에이터(0002)로 로그인한다.
 */

const CREATOR_PHONE = "01000000002"; // seed_demo 데모 크리에이터(010-0000-0002) — stellar 오너.

// 1x1 PNG — Pillow가 생성한 **실제로 디코딩되는** 최소 이미지. 서버의 content-type/매직바이트
// 게이트(415/422)와 ASS-271 Pillow decode-verify(청크 CRC·구조 검사)를 모두 통과한다.
// (이전 리터럴은 IDAT 청크 CRC가 깨진 손상 PNG였다 — magic-byte sniff만 통과해 verify 도입
//  전까지만 우연히 통과했고, ASS-271 이후 서버가 422로 정당하게 거부해 이 저니가 깨졌었다.)
const TINY_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC",
  "base64",
);

test("스튜디오 포스트 작성 — 이미지 업로드 → 발행 → 스튜디오 노출", async ({ page }) => {
  const body = `업로드 저니 ${Date.now()}`;

  // 1. 데모 크리에이터 OTP 로그인.
  await test.step("OTP 로그인(크리에이터)", async () => {
    await page.goto("/login", { waitUntil: "networkidle" });
    const phoneField = page.getByLabel("휴대폰 번호");
    await expect(phoneField, "OTP 로그인 폼(live 모드) 렌더").toBeVisible();
    await phoneField.fill(CREATOR_PHONE);
    await page.getByRole("button", { name: "인증번호 받기" }).click();
    await page.getByRole("group", { name: "인증 코드" }).waitFor({ timeout: 10_000 });

    const code = otpFor(CREATOR_PHONE);
    await typeOtp(page, code);
    const loginBtn = page.getByRole("button", { name: "로그인" });
    try {
      await loginBtn.click({ timeout: 5_000 });
    } catch {
      await page.getByLabel("자리 1").click();
      for (let i = 0; i < 6; i++) await page.keyboard.press("Backspace");
      await typeOtp(page, code, 120);
      await loginBtn.click({ timeout: 5_000 });
    }
    await page.waitForURL("**/discovery", { timeout: 25_000 });
  });

  // 2. 포스트 작성 화면 — 본문 입력 + 이미지 업로드(POST /api/uploads) → 프리뷰 확인 → 발행.
  await test.step("이미지 업로드 + 발행", async () => {
    await page.goto("/studio/posts/new", { waitUntil: "networkidle" });
    // 제목·본문 모두 입력 — 컴포저는 제목을 필수로 요구한다(validateComposerDraft).
    // 제목이 비면 발행 버튼이 조용히 막혀(publish()가 조기 return) /studio 이동이
    // 일어나지 않으므로, 저니가 성립하려면 제목을 반드시 채워야 한다.
    await page.getByLabel("제목").fill("업로드 저니 제목");
    await page.getByLabel("본문").fill(body);

    // 숨김 file input에 작은 PNG 주입 → onChange가 apiUpload를 트리거(업로드 중 로딩 → 프리뷰).
    await page.locator('input[type="file"]').setInputFiles({
      name: "shot.png",
      mimeType: "image/png",
      buffer: TINY_PNG,
    });
    // 업로드 성공 시 media_url 프리뷰가 렌더된다(서버 왕복 완료 신호).
    await expect(page.getByAltText("업로드한 이미지 미리보기")).toBeVisible({ timeout: 20_000 });

    await page.getByRole("button", { name: "발행하기" }).click();
    // 발행 성공 → /studio로 이동.
    await page.waitForURL("**/studio", { timeout: 20_000 });
  });

  // 3. 스튜디오 포스트 목록 노출 + media_url이 업로드 경로(/media/uploads/…)인지 API로 확인.
  await test.step("스튜디오 노출 + media_url 확인", async () => {
    await page.goto("/studio/posts", { waitUntil: "networkidle" });
    await expect(page.getByText(body).first()).toBeVisible({ timeout: 10_000 });

    // 오너 스코프 목록에서 방금 발행한 포스트를 찾아 media_url이 업로드 산출물인지 단언.
    const resp = await page.request.get("/api/studio/posts");
    expect(resp.ok(), "GET /api/studio/posts 200").toBeTruthy();
    const data = await resp.json();
    const items: { body?: string; media_url?: string }[] = data.items ?? data;
    const mine = items.find((p) => (p.body ?? "").includes(body));
    expect(mine, "발행한 포스트가 오너 목록에 존재").toBeTruthy();
    expect(mine?.media_url, "업로드 media_url이 포스트에 반영").toMatch(/\/media\/uploads\//);
  });
});

/** OTP 6자리를 첫 자리부터 순차 타이핑(자동 포커스 이동 활용) — journey.spec.ts와 동일 로직. */
async function typeOtp(page: Page, code: string, delay = 80): Promise<void> {
  await page.getByLabel("자리 1").click();
  await page.keyboard.type(code, { delay });
}
