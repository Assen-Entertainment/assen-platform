import { test, expect, type Page } from "@playwright/test";
import { otpFor } from "./helpers/otp";

/**
 * 정본 통합 저니 — 웹(Next, live 모드) + 서버(Django, seed_demo) 결합.
 * 기존 scripts/integration-smoke.mjs의 14스텝을 Playwright Test로 이관(단언·auto-wait·trace·재시도).
 *
 * 전제: Django 127.0.0.1:8000(dev·mock OTP·seed_demo), Next(NEXT_PUBLIC_API_URL=/api·rewrites)가
 *       playwright.config baseURL로 접근 가능. 서버 기동 절차는 playwright.config 주석 참조.
 * 저니: OTP 로그인 → 세션 → 팔로우 → 좋아요·댓글 → 신고 → 상품상세·주문(배송지) →
 *       주문목록 → 알림 → 계정수정 → 결제수단 → KYC → 로그아웃
 */

const PHONE = "01000000001"; // seed_demo 데모팬(010-0000-0001) — OTP 로그인 결정적.
const NEWNICK = "스모크수정";

/**
 * 로그인 전 익명 상태에서 의도적으로 401 이 나는 프로브 URL 화이트리스트.
 * 이 URL 의 401 만 무시하고, 로그인 이후 다른 URL 의 401 은 진짜 회귀로 실패시킨다.
 */
const ANON_401_PROBES = ["/fan/me"];

/**
 * favicon 404, 그리고 익명 프로브(ANON_401_PROBES)의 의도된 401 만 비-에러 노이즈로 무시한다.
 * `entry` 는 콘솔 핸들러가 만든 "메시지 @ URL" 형태 — 401 은 실패 리소스 URL 로 화이트리스트를 판정한다
 * (모든 401 을 뭉뚱그려 삼키면 로그인 후 인증 회귀를 놓치므로 URL 로 좁힌다).
 */
function isRelevantConsoleError(entry: string): boolean {
  if (entry.includes("favicon")) return false;
  if (entry.includes("status of 401")) return !ANON_401_PROBES.some((u) => entry.includes(u));
  return true;
}

test("팬 저니 — 로그인부터 로그아웃까지(14스텝)", async ({ page }) => {
  const consoleErrors: string[] = [];
  // 리소스 401 등 네트워크 실패는 실패 URL 이 m.location().url 에 담긴다 → "메시지 @ URL" 로 보존해
  // isRelevantConsoleError 가 익명 프로브 화이트리스트를 URL 로 판정할 수 있게 한다.
  page.on("console", (m) => {
    if (m.type() !== "error") return;
    const url = m.location().url;
    consoleErrors.push(url ? `${m.text()} @ ${url}` : m.text());
  });
  page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));

  // 1. OTP 로그인 -----------------------------------------------------------
  await test.step("OTP 로그인", async () => {
    await page.goto("/login", { waitUntil: "networkidle" });
    const phoneField = page.getByLabel("휴대폰 번호");
    await expect(phoneField, "OTP 로그인 폼(live 모드) 렌더").toBeVisible();
    await phoneField.fill(PHONE);
    await page.getByRole("button", { name: "인증번호 받기" }).click();
    await page.getByRole("group", { name: "인증 코드" }).waitFor({ timeout: 10_000 });

    const code = otpFor(PHONE);
    // 자동 포커스 이동과 fill()의 경합(상태 어긋남) 회피 — 사람처럼 순차 타이핑.
    await typeOtp(page, code);
    const loginBtn = page.getByRole("button", { name: "로그인" });
    try {
      await loginBtn.click({ timeout: 5_000 });
    } catch {
      // 버튼이 비활성(상태 미완성)이면 지우고 1회 재입력.
      await page.getByLabel("자리 1").click();
      for (let i = 0; i < 6; i++) await page.keyboard.press("Backspace");
      await typeOtp(page, code, 120);
      await loginBtn.click({ timeout: 5_000 });
    }
    await page.waitForURL("**/discovery", { timeout: 25_000 });
  });

  // 2. 세션 반영 (mypage 시드 닉네임) — 재실행 내성: 데모팬 또는 편집된 닉네임 허용.
  await test.step("세션 me 반영", async () => {
    await page.goto("/mypage", { waitUntil: "networkidle" });
    await expect(page.getByText(/데모팬|스모크수정/).first()).toBeVisible();
  });

  // 3. 팔로우 토글 (rabbit) — 서버 왕복 후 상태 반전 확인.
  await test.step("팔로우 토글", async () => {
    await page.goto("/creator/rabbit", { waitUntil: "networkidle" });
    const followBtn = page.getByRole("button", { name: /^(팔로우|팔로잉)$/ }).first();
    await followBtn.waitFor({ timeout: 10_000 });
    // 세션 반영(클라 쿼리 settle) 전에 읽으면 클릭 시점 상태와 어긋난다 — 텍스트 안정화 대기.
    const before = await stabilizeText(followBtn);
    const expected = before === "팔로우" ? "팔로잉" : "팔로우";
    // 쿼리 settle 리렌더로 클릭이 유실될 수 있음 — 반영 확인+재시도(최대 3회).
    await expect(async () => {
      await followBtn.click();
      await expect(followBtn).toHaveText(expected, { timeout: 3_500 });
    }).toPass({ timeout: 20_000 });
  });

  // 4. 피드 → 첫 포스트 상세 → 좋아요 + 댓글.
  await test.step("좋아요 토글 + 댓글 작성", async () => {
    await page.goto("/feed", { waitUntil: "networkidle" });
    await page.locator("article a[href^='/post/']").first().click();
    await page.waitForURL("**/post/**", { timeout: 10_000 });

    const likeBtn = page.getByRole("button", { name: /좋아요/ }).first();
    const likedBefore = (await likeBtn.getAttribute("aria-pressed")) === "true";
    await likeBtn.click();
    // 서버 왕복+invalidate 후 aria-pressed 반전.
    await expect(likeBtn).toHaveAttribute("aria-pressed", String(!likedBefore), { timeout: 5_000 });

    const commentBody = `통합 스모크 ${Date.now()}`;
    await page.locator("textarea, input[placeholder*='댓글']").first().fill(commentBody);
    await page.getByRole("button", { name: /등록|게시|작성/ }).first().click();
    await expect(page.getByText(commentBody).first()).toBeVisible({ timeout: 10_000 });
  });

  // 4b. 피드 신고 저니 (더보기 → 신고하기 → 사유 → 제출 → 접수 토스트).
  await test.step("피드 신고 접수", async () => {
    await page.goto("/feed", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "더보기" }).first().click();
    await page.getByRole("button", { name: "신고하기" }).click({ timeout: 10_000 });
    // 신고 사유 라디오(서버 FAN_REPORTABLE_TYPES 정렬) 첫 항목 선택 후 제출.
    await page.getByRole("radio").first().click({ timeout: 10_000 });
    await page.getByRole("button", { name: "신고 제출" }).click();
    await expect(page.getByText("신고가 접수되었어요").first()).toBeVisible({ timeout: 10_000 });
  });

  // 5. 상품 구매 → 주문 완료 — 최신순 첫 카드가 품절일 수 있어 API로 주문 가능 상품 선택 후 상세 직행.
  await test.step("상품 상세 → 주문 생성(배송지 포함)", async () => {
    const productsResp = await page.request.get("/api/products");
    const productsBody = await productsResp.json();
    const orderable = (productsBody.items ?? productsBody).find(
      (p: { sold_out?: boolean; locked?: boolean }) => !p.sold_out && !p.locked,
    );
    expect(orderable, "주문 가능 상품 존재(API)").toBeTruthy();

    await page.goto(`/store/${orderable.id}`, { waitUntil: "networkidle" });
    await expect(page.getByText(orderable.title).first()).toBeVisible();
    await page.getByRole("button", { name: /구매|예약|받기/ }).first().click();
    await page.waitForURL("**/checkout**", { timeout: 30_000 });

    // 동의 체크(Radix role=checkbox — native input 아님). 렌더 완료 후 전부 체크.
    const consents = page.getByRole("checkbox");
    await consents.first().waitFor({ timeout: 10_000 });
    const n = await consents.count();
    for (let i = 0; i < n; i++) {
      const box = consents.nth(i);
      if ((await box.getAttribute("aria-checked")) !== "true") await box.click();
    }
    // 배송 상품(굿즈)이면 배송지 필수(W1A 계약: 누락 시 422 ShippingAddressRequired).
    const recipient = page.getByLabel("받는 분");
    if (await recipient.count()) {
      await recipient.fill("스모크 배송");
      await page.getByLabel("연락처").fill("010-0000-0002");
      await page.getByLabel("우편번호").fill("04524");
      await page.getByLabel("주소", { exact: true }).fill("서울 중구 세종대로 110");
      await page.getByLabel("상세 주소").fill("1203호");
    }
    await page.getByRole("button", { name: /결제하기/ }).click({ timeout: 15_000 });
    await page.waitForURL("**/checkout/complete**", { timeout: 30_000 });
    await expect(page.getByText(/ASN-/).first(), "완료 화면 주문번호(ASN-)").toBeVisible();
  });

  // 6. 주문 목록에 실 주문 존재.
  await test.step("주문 목록", async () => {
    await page.goto("/orders", { waitUntil: "networkidle" });
    await expect(page.getByText(/ASN-/).first()).toBeVisible();
  });

  // 7. 알림 (주문 알림 ≥1) + 모두 읽음.
  await test.step("알림 화면", async () => {
    await page.goto("/notifications", { waitUntil: "networkidle" });
    const readAll = page.getByRole("button", { name: /모두 읽음/ });
    if (await readAll.count()) await readAll.click();
  });

  // 7.5 계정 수정 (PATCH /fan/me nickname) — 닉네임을 고유값으로 바꿔 영속 확인.
  await test.step("계정 수정 — 닉네임 영속", async () => {
    await page.goto("/settings/account", { waitUntil: "networkidle" });
    const nickField = page.getByLabel("닉네임");
    await nickField.waitFor({ timeout: 10_000 });
    await nickField.fill(NEWNICK);
    await page.getByRole("button", { name: "저장" }).first().click();
    await expect(page.getByText("저장되었어요").first()).toBeVisible({ timeout: 10_000 });
    // 재조회로 영속 확인(PATCH /fan/me).
    await page.goto("/settings/account", { waitUntil: "networkidle" });
    await expect(page.getByLabel("닉네임")).toHaveValue(NEWNICK, { timeout: 10_000 });
  });

  // 7.6 결제수단 등록(mock PG 토큰 — raw PAN 미전송).
  await test.step("결제수단 등록", async () => {
    await page.goto("/settings/payments", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "카드 등록" }).first().click();
    // 다이얼로그 확인 버튼 = "등록"("결제 수단 등록"은 제목). 브랜드 기본값으로 등록.
    await page.getByRole("button", { name: "등록", exact: true }).click({ timeout: 10_000 });
    await expect(page.getByText("결제 수단이 등록되었어요").first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/••••/).first()).toBeVisible({ timeout: 5_000 });
  });

  // 7.7 본인인증(KYC) — age-gate: 동의 → 성인 인증하기 → 입장(성공) → 재방문 세션 반영.
  await test.step("본인인증(KYC mock) — 세션 반영", async () => {
    await page.goto("/age-gate", { waitUntil: "networkidle" });
    // "전체 동의" 마스터 하나로 필수 3종 일괄 체크(개별 루프의 상태전파 경합 회피).
    await page.getByText("전체 동의").click();
    await page.getByRole("button", { name: "성인 인증하기" }).click({ timeout: 15_000 });
    await page.waitForURL("**/discovery", { timeout: 15_000 });
    // 재방문 시 세션 adult_verified 반영("이미 본인인증") — 서버 영속 + /fan/me 재조회 검증.
    await page.goto("/age-gate", { waitUntil: "networkidle" });
    await expect(page.getByText("이미 본인인증이 완료되었어요").first()).toBeVisible({ timeout: 10_000 });
  });

  // 8. 로그아웃 → 세션 소거.
  await test.step("로그아웃", async () => {
    await page.goto("/settings", { waitUntil: "networkidle" });
    // 하드 sleep 대신 로그아웃 POST(서버 쿠키 소거) 완료를 조건 대기 — 그래야 이후 /mypage 재조회가
    // 확정적으로 미인증(쿠키 없음)이 된다. 응답 대기 등록 후 클릭해 경합을 없앤다.
    const logoutDone = page.waitForResponse(
      (r) => r.url().includes("/fan/logout") && r.request().method() === "POST",
      { timeout: 15_000 },
    );
    await page.getByText("로그아웃").first().click();
    await logoutDone;
    await page.goto("/mypage", { waitUntil: "networkidle" });
    await expect(page.getByText(NEWNICK)).toHaveCount(0);
  });

  // 콘솔 에러(비-favicon·비-401)가 남으면 저니는 통과했어도 실패로 승격(모순 제거).
  const relevant = consoleErrors.filter(isRelevantConsoleError);
  expect.soft(relevant, `콘솔 에러 없음: ${relevant.slice(0, 5).join(" | ")}`).toEqual([]);
});

/** OTP 6자리를 첫 자리부터 순차 타이핑(자동 포커스 이동 활용). */
async function typeOtp(page: Page, code: string, delay = 80): Promise<void> {
  await page.getByLabel("자리 1").click();
  await page.keyboard.type(code, { delay });
}

/** 클라 쿼리 settle 리렌더로 텍스트가 흔들리는 버튼의 안정화된 텍스트를 반환. */
async function stabilizeText(locator: import("@playwright/test").Locator): Promise<string> {
  let text = (await locator.textContent())?.trim() ?? "";
  for (let i = 0; i < 6; i++) {
    await locator.page().waitForTimeout(500);
    const now = (await locator.textContent())?.trim() ?? "";
    if (now === text) break;
    text = now;
  }
  return text;
}
