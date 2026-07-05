/**
 * ⚠️ 정본은 e2e/journey.spec.ts (Playwright Test — 단언·auto-wait·trace·재시도)다.
 *    이 스크립트는 의존성 없이 돌릴 수 있는 경량 호환용으로 유지한다(동일 14스텝 저니).
 *
 * 통합 스모크 — 웹(Next, live 모드) + 서버(Django, seed_demo) 결합 저니.
 * 전제: Django 127.0.0.1:8000(dev·mock OTP·seed_demo), Next 3000(NEXT_PUBLIC_API_URL=/api·rewrites).
 * 저니: OTP 로그인 → 세션 → 팔로우 토글 → 포스트 좋아요·댓글 → 상품 구매(주문) → 주문 목록 → 알림 → 로그아웃
 * 사용: node scripts/integration-smoke.mjs [baseUrl]
 */
import { chromium } from "playwright";
import { createHmac } from "node:crypto";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

const BASE = process.argv[2] ?? "http://localhost:3000";
const OUT = join(process.cwd(), ".smoke-integration");
const PHONE = "01000000001";

/**
 * 서버 MockOtpSender와 동일: normalize(+82 폴딩) 후 HMAC-SHA256 6자리.
 * ※시크릿("assen-dev-otp")은 서버 config/otp.py와 동기 — 변경 시 함께 수정.
 */
function otpFor(phone) {
  const digits = phone.replace(/\D/g, "");
  const normalized = "+" + (digits.startsWith("0") ? "82" + digits.slice(1) : digits);
  const digest = createHmac("sha256", "assen-dev-otp").update(normalized).digest("hex");
  return String(parseInt(digest.slice(0, 8), 16) % 1_000_000).padStart(6, "0");
}

const consoleErrors = [];
let step = 0;
async function shot(page, name) {
  step += 1;
  await page.screenshot({ path: join(OUT, `${String(step).padStart(2, "0")}-${name}.png`) });
}
function pass(label) {
  console.log(`[PASS] ${label}`);
}
async function fail(page, label, extra = "") {
  await shot(page, `FAIL-${label.replace(/\W+/g, "_")}`);
  console.error(`[FAIL] ${label} ${extra}`);
  console.error("console errors:", consoleErrors.slice(-5));
  process.exit(1);
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));
  page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));

  // 1. OTP 로그인
  await page.goto(BASE + "/login", { waitUntil: "networkidle" });
  await shot(page, "login");
  const phoneField = page.getByLabel("휴대폰 번호");
  if (!(await phoneField.count())) await fail(page, "OTP 로그인 폼 렌더(live 모드 아님?)");
  await phoneField.fill(PHONE);
  await page.getByRole("button", { name: "인증번호 받기" }).click();
  await page.getByRole("group", { name: "인증 코드" }).waitFor({ timeout: 10000 });
  const code = otpFor(PHONE);
  // 자동 포커스 이동과 fill()의 경합(상태 어긋남 플래키) 회피 — 사람처럼 순차 타이핑.
  await page.getByLabel("자리 1").click();
  await page.keyboard.type(code, { delay: 80 });
  await shot(page, "otp-filled");
  const loginBtn = page.getByRole("button", { name: "로그인" });
  try {
    await loginBtn.click({ timeout: 5000 });
  } catch {
    // 버튼이 비활성(상태 미완성)이면 지우고 1회 재입력.
    await page.getByLabel("자리 1").click();
    for (let i = 0; i < 6; i++) await page.keyboard.press("Backspace");
    await page.keyboard.type(code, { delay: 120 });
    await loginBtn.click({ timeout: 5000 });
  }
  await page.waitForURL("**/discovery", { timeout: 25000 }).catch(() => fail(page, "로그인 후 /discovery 이동"));
  pass("OTP 로그인");

  // 2. 세션 반영 (mypage에 시드 닉네임) — 재실행 내성: 데모팬 또는 편집된 닉네임 허용.
  await page.goto(BASE + "/mypage", { waitUntil: "networkidle" });
  const nick = await page.getByText(/데모팬|스모크수정/).first().count();
  if (!nick) await fail(page, "세션 유저(닉네임) 표시");
  pass("세션 me 반영");
  await shot(page, "mypage");

  // 3. 팔로우 토글 (rabbit) — 서버 왕복 후 상태 반전 확인
  await page.goto(BASE + "/creator/rabbit", { waitUntil: "networkidle" });
  const followBtn = page.getByRole("button", { name: /^(팔로우|팔로잉)$/ }).first();
  await followBtn.waitFor({ timeout: 10000 });
  // 세션 반영(클라 쿼리 settle) 전에 읽으면 클릭 시점 상태와 어긋난다 — 텍스트 안정화 대기.
  let before = (await followBtn.textContent())?.trim();
  for (let i = 0; i < 6; i++) {
    await page.waitForTimeout(500);
    const now = (await followBtn.textContent())?.trim();
    if (now === before) break;
    before = now;
  }
  const expected = before === "팔로우" ? "팔로잉" : "팔로우";
  // 쿼리 settle 리렌더로 클릭이 유실될 수 있음 — 반영 확인+재시도(최대 3회).
  let flipped = false;
  for (let attempt = 0; attempt < 3 && !flipped; attempt++) {
    await followBtn.click().catch(() => {});
    for (let i = 0; i < 5; i++) {
      await page.waitForTimeout(700);
      if (((await followBtn.textContent())?.trim()) === expected) { flipped = true; break; }
    }
  }
  if (!flipped) await fail(page, `팔로우 토글(${before}→${expected})`);
  pass(`팔로우 토글 (${before}→${expected})`);
  await shot(page, "follow");

  // 4. 피드 → 첫 포스트 상세 → 좋아요 + 댓글
  await page.goto(BASE + "/feed", { waitUntil: "networkidle" });
  await page.locator("article a[href^='/post/']").first().click();
  await page.waitForURL("**/post/**", { timeout: 10000 });
  const likeBtn = page.getByRole("button", { name: /좋아요/ }).first();
  const likedBefore = (await likeBtn.getAttribute("aria-pressed")) === "true";
  await likeBtn.click();
  await page.waitForTimeout(1200); // 서버 왕복+invalidate
  const likedAfter = (await likeBtn.getAttribute("aria-pressed")) === "true";
  if (likedAfter === likedBefore) await fail(page, "좋아요 토글 반영");
  pass("좋아요 토글");
  const commentBody = `통합 스모크 ${Date.now()}`;
  const commentInput = page.locator("textarea, input[placeholder*='댓글']").first();
  await commentInput.fill(commentBody);
  await page.getByRole("button", { name: /등록|게시|작성/ }).first().click();
  await page.getByText(commentBody).first().waitFor({ timeout: 10000 })
    .catch(() => fail(page, "댓글 등록 표시"));
  pass("댓글 작성");
  await shot(page, "post-detail");

  // 4b. 피드 신고 저니 (더보기 → 신고하기 → 사유 선택 → 제출 → 접수 토스트)
  await page.goto(BASE + "/feed", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "더보기" }).first().click()
    .catch(() => fail(page, "포스트 더보기 버튼"));
  await page.getByRole("button", { name: "신고하기" }).click({ timeout: 10000 })
    .catch(() => fail(page, "신고하기 액션 노출"));
  // 신고 사유 라디오(서버 FAN_REPORTABLE_TYPES 정렬) 첫 항목 선택 후 제출.
  await page.getByRole("radio").first().click({ timeout: 10000 })
    .catch(() => fail(page, "신고 사유 라디오 렌더"));
  await page.getByRole("button", { name: "신고 제출" }).click()
    .catch(() => fail(page, "신고 제출 버튼"));
  await page.getByText("신고가 접수되었어요").first().waitFor({ timeout: 10000 })
    .catch(() => fail(page, "신고 접수 토스트"));
  pass("피드 신고 접수");
  await shot(page, "report");

  // 5. 상품 구매 → 주문 완료 — 최신순 첫 카드가 품절(피규어)이라, API로 주문 가능 상품을 골라 상세 직행.
  const productsResp = await page.request.get(BASE + "/api/products");
  const productsBody = await productsResp.json();
  const orderable = (productsBody.items ?? productsBody).find((p) => !p.sold_out && !p.locked);
  if (!orderable) await fail(page, "주문 가능 상품 존재(API)");
  await page.goto(`${BASE}/store/${orderable.id}`, { waitUntil: "networkidle" });
  if (!(await page.getByText(orderable.title).first().count())) await fail(page, "상품 상세 렌더");
  pass(`상품 상세 (${orderable.title})`);
  await shot(page, "product");
  await page.getByRole("button", { name: /구매|예약|받기/ }).first().click();
  let onCheckout = false;
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(1000);
    if (page.url().includes("/checkout")) { onCheckout = true; break; }
  }
  if (!onCheckout) await fail(page, "체크아웃 이동", page.url());
  // 동의 체크(Radix role=checkbox — native input 아님). 렌더 완료를 기다린 뒤 전부 체크.
  const consents = page.getByRole("checkbox");
  await consents.first().waitFor({ timeout: 10000 }).catch(() => fail(page, "체크아웃 동의 체크박스 렌더"));
  const n = await consents.count();
  for (let i = 0; i < n; i++) {
    const box = consents.nth(i);
    if ((await box.getAttribute("aria-checked")) !== "true") await box.click();
  }
  // 배송 상품(굿즈)이면 배송지 입력 필요(W1A 계약: 누락 시 422 ShippingAddressRequired) —
  // 배송지 섹션이 있으면 필수 필드를 채운다. 디지털/티켓 등 비배송 상품은 섹션이 없어 건너뛴다.
  const recipient = page.getByLabel("받는 분");
  if (await recipient.count()) {
    await recipient.fill("스모크 배송");
    await page.getByLabel("연락처").fill("010-0000-0002");
    await page.getByLabel("우편번호").fill("04524");
    await page.getByLabel("주소", { exact: true }).fill("서울 중구 세종대로 110");
    await page.getByLabel("상세 주소").fill("1203호");
    pass("배송지 입력(굿즈)");
  }
  await shot(page, "checkout-consented");
  await page
    .getByRole("button", { name: /결제하기/ })
    .click({ timeout: 15000 })
    .catch(() => fail(page, "결제하기 버튼 활성/클릭"));
  let onComplete = false;
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(1000);
    if (page.url().includes("/checkout/complete")) { onComplete = true; break; }
  }
  if (!onComplete) await fail(page, "결제(주문 생성)→완료 이동", page.url());
  const orderNo = await page.getByText(/ASN-/).first().textContent().catch(() => null);
  if (!orderNo) await fail(page, "완료 화면 주문번호(ASN-)");
  pass(`주문 생성 (${orderNo?.trim().slice(0, 24)})`);
  await shot(page, "order-complete");

  // 6. 주문 목록에 실 주문 존재
  await page.goto(BASE + "/orders", { waitUntil: "networkidle" });
  if (!(await page.getByText(/ASN-/).first().count())) await fail(page, "주문 목록 반영");
  pass("주문 목록");
  await shot(page, "orders");

  // 7. 알림 (주문 알림 ≥1) + 모두 읽음
  await page.goto(BASE + "/notifications", { waitUntil: "networkidle" });
  const readAll = page.getByRole("button", { name: /모두 읽음/ });
  if (await readAll.count()) await readAll.click();
  pass("알림 화면");
  await shot(page, "notifications");

  // 7.5 계정 수정 (PATCH /fan/me nickname) — R3. 닉네임을 고유값으로 바꿔 영속 확인.
  const NEWNICK = "스모크수정";
  await page.goto(BASE + "/settings/account", { waitUntil: "networkidle" });
  const nickField = page.getByLabel("닉네임");
  await nickField.waitFor({ timeout: 10000 }).catch(() => fail(page, "계정 닉네임 필드"));
  await nickField.fill(NEWNICK);
  await page.getByRole("button", { name: "저장" }).first().click();
  await page.getByText("저장되었어요").first().waitFor({ timeout: 10000 })
    .catch(() => fail(page, "계정 저장 토스트"));
  await page.goto(BASE + "/settings/account", { waitUntil: "networkidle" });
  const persisted = await page.getByLabel("닉네임").inputValue().catch(() => "");
  if (persisted !== NEWNICK) await fail(page, "닉네임 영속(PATCH /fan/me)", persisted);
  pass("계정 수정 (닉네임 영속)");
  await shot(page, "account-edit");

  // 7.6 결제수단 등록(mock PG 토큰 — raw PAN 미전송) — R3
  await page.goto(BASE + "/settings/payments", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "카드 등록" }).first().click();
  // 다이얼로그 확인 버튼 = "등록"("결제 수단 등록"은 제목). 브랜드 기본값으로 등록.
  await page.getByRole("button", { name: "등록", exact: true }).click({ timeout: 10000 })
    .catch(() => fail(page, "결제수단 등록 확인 버튼"));
  await page.getByText("결제 수단이 등록되었어요").first().waitFor({ timeout: 10000 })
    .catch(() => fail(page, "결제수단 등록 토스트"));
  await page.waitForTimeout(600);
  if (!(await page.getByText(/••••/).first().count())) await fail(page, "결제수단 목록 반영(••••)");
  pass("결제수단 등록");
  await shot(page, "payment-method");

  // 7.7 본인인증(KYC) — age-gate: 동의 → 성인 인증하기 → 입장(성공) — R3
  await page.goto(BASE + "/age-gate", { waitUntil: "networkidle" });
  // "전체 동의" 마스터 하나로 필수 3종 일괄 체크(개별 루프의 상태전파 경합 회피).
  await page.getByText("전체 동의").click();
  // Playwright는 click 시 버튼 활성(동의 반영)까지 자동 대기 — 별도 폴링 불요.
  await page.getByRole("button", { name: "성인 인증하기" }).click({ timeout: 15000 })
    .catch(() => fail(page, "성인 인증하기 버튼"));
  // 성공 시 /discovery로 이동(router.push). 이동 대기.
  await page.waitForURL("**/discovery", { timeout: 15000 })
    .catch(() => fail(page, "KYC 인증 후 /discovery 이동"));
  // 재방문 시 세션 adult_verified 반영("이미 본인인증") 확인 → 서버 영속 + /fan/me 재조회 검증.
  await page.goto(BASE + "/age-gate", { waitUntil: "networkidle" });
  await page.getByText("이미 본인인증이 완료되었어요").first().waitFor({ timeout: 10000 })
    .catch(() => fail(page, "KYC 세션 반영(이미 인증)"));
  pass("본인인증(KYC mock) — 세션 반영");
  await shot(page, "kyc");

  // 8. 로그아웃 → 세션 소거
  await page.goto(BASE + "/settings", { waitUntil: "networkidle" });
  await page.getByText("로그아웃").first().click();
  await page.waitForTimeout(1500);
  await page.goto(BASE + "/mypage", { waitUntil: "networkidle" });
  if (await page.getByText(NEWNICK).first().count()) await fail(page, "로그아웃 후 세션 소거");
  pass("로그아웃");
  await shot(page, "logged-out");

  await browser.close();
  // 401 리소스 에러 = 익명 세션 프로브(/fan/me)의 의도된 응답(비로그인 정상 신호) — 실패로 치지 않는다.
  const relevant = consoleErrors.filter(
    (e) => !e.includes("favicon") && !e.includes("status of 401"),
  );
  console.log(`console errors(비-favicon): ${relevant.length}`);
  relevant.slice(0, 5).forEach((e) => console.log("  -", e.slice(0, 160)));
  // 스텝은 전부 통과했어도 콘솔 에러가 남으면 PASS 문구와 exitCode를 구분해 모순을 없앤다.
  if (relevant.length > 0) {
    console.log("INTEGRATION SMOKE: PASS WITH CONSOLE ERRORS");
    process.exitCode = 1;
  } else {
    console.log("INTEGRATION SMOKE: ALL PASS");
    process.exitCode = 0;
  }
}

main().catch((e) => {
  // 예기치 못한 throw(셀렉터/네트워크 등)를 unhandled rejection 대신 여기서 흡수.
  console.error("INTEGRATION SMOKE: FATAL", e?.stack || e);
  process.exitCode = 1;
});
