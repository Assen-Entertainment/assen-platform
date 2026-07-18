import { test, expect } from "@playwright/test";
import { DEMO_CREATOR_EMAIL, DEMO_PASSWORD, loginViaEmail } from "./helpers/auth";

/**
 * 스튜디오 포스트 작성 with 이미지 업로드(R12) — 웹(Next, live 모드) + 서버(Django, seed_demo) 결합.
 * 데모 크리에이터(stellar 오너)로 로그인 → 작은 PNG를 POST /api/uploads로 업로드 →
 * 반환 media_url을 실은 포스트를 발행 → 스튜디오 포스트 목록 노출 + media_url이 /media/uploads/… 확인
 * → **그 media_url을 실제로 GET해 200 + image/*를 확인**(문자열 단언만으로는 못 잡는 라우팅 결함).
 *
 * 전제(journey.spec.ts와 동일): Django 127.0.0.1:8000(dev·seed_demo·ALLOW_UPLOADS on —
 *   dev.py:28에서 켜진다. 과거의 SERVE_LOCAL_MEDIA 플래그는 폐지됐고, 미디어는 이제 모든
 *   백엔드에서 Django의 게이트된 뷰가 서빙한다),
 *   Next(NEXT_PUBLIC_API_URL=/api·rewrites)가 playwright.config baseURL로 접근 가능.
 * ※발행은 오너(크리에이터)만 가능하므로 데모팬이 아닌 데모 크리에이터로 로그인한다.
 */

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
  let mediaUrl = "";

  // 1. 데모 크리에이터 이메일 로그인.
  await test.step("이메일 로그인(크리에이터)", async () => {
    await loginViaEmail(page, DEMO_CREATOR_EMAIL, DEMO_PASSWORD);
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
    mediaUrl = mine?.media_url ?? "";
  });

  // 4. ★ media_url을 실제로 GET한다 — 문자열 단언만으로는 원리적으로 못 잡는 회귀.
  //
  // 왜 이 스텝이 따로 필요한가: 위 3번은 "URL이 올바른 모양인가"만 본다. URL이 완벽한 모양이면서
  // 아무것도 돌려주지 않는 상태가 실재했다(라우팅 누락). 그리고 그 실패는 UI에서 **보이지 않는다** —
  // MediaImage(components/ui/media-image.tsx)의 onError 폴백이 조용히 그라디언트
  // 플레이스홀더로 되돌리므로, 깨진 이미지가 의도된 디자인처럼 렌더된다. 위 2번의
  // `getByAltText(...).toBeVisible()`도 증거가 못 된다 — <img>는 src가 404여도 visible이다.
  // 실 바이트를 받아보는 단언만이 이 클래스의 결함을 잡는다.
  //
  // ⚠️ 이 테스트가 증명하지 **못하는** 것 — ALB 리스너 규칙:
  // CI/로컬은 Next(:3000) + Django(:8000)를 직접 띄운다(.github/workflows/e2e.yml) — **ALB가 없다**.
  // 따라서 이 GET이 타는 경로는 `브라우저 → Next → next.config.mjs rewrite → Django`이고,
  // 이것이 검증하는 것은 **앱 레벨 경로**(Django의 게이트된 /media 뷰 + Next rewrite)뿐이다.
  // 프로덕션의 실제 경로는 `브라우저 → 단일 ALB 오리진 → 리스너 규칙 → Django`로 **다른 hop**이며,
  // `infra/terraform/web.tf`의 path_pattern에 `/media/*`가 실려 있는지는 **이 스위트가 절대 못 잡는다**.
  // 그건 apply 후 사람이 확인해야 한다(런북 §3-5). 이 테스트가 green이라고 prod 미디어가
  // 산다고 믿지 말 것 — 두 레이어는 독립적으로 깨진다.
  await test.step("media_url 실 GET → 200 + image/* (ALB 아님, 앱 레벨 경로)", async () => {
    // 사이트 상대 URL → baseURL(Next)로 해석된다 — 브라우저 <img src>가 타는 경로와 동일.
    const res = await page.request.get(mediaUrl);
    expect(res.status(), `GET ${mediaUrl} → 200 (404면 /media 라우팅이 끊긴 것)`).toBe(200);
    // image/* 단언은 두 결함을 동시에 잡는다: (a) 라우팅이 HTML 404 페이지를 돌려주는 경우,
    // (b) Upload 행 조회 실패로 media.py가 _UNVOUCHED_CONTENT_TYPE(application/octet-stream)을
    //     붙이는 경우 — 후자는 200이지만 브라우저가 이미지로 렌더하지 않는다.
    expect(res.headers()["content-type"], "content-type이 image/* (octet-stream이면 행 조회 실패)").toMatch(
      /^image\//,
    );
    // 200 + 빈 바디(스트리밍 결함)를 배제. 업로드 파이프라인이 메타데이터를 제거하며 재인코딩하므로
    // 원본 바이트와의 동일성은 단언하지 않는다(정당하게 다르다) — 비어있지 않음만 본다.
    expect((await res.body()).byteLength, "이미지 바디가 비어있지 않음").toBeGreaterThan(0);
  });
});
