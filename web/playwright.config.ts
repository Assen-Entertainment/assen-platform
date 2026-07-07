import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright Test 정본 설정 — R6-W1B.
 *
 * 전제(외부 기동): 이 설정은 **webServer를 띄우지 않는다**. Django(seed_demo·mock OTP)와
 * Next(live 모드) 서버는 외부에서 먼저 기동한 뒤 실행한다(로컬 절차는 아래 주석, CI 배선은
 * R6-W3에서 담당). baseURL은 PLAYWRIGHT_BASE_URL로 주입(기본 http://localhost:3000).
 *
 * 서버 기동(로컬, 메모리 절차):
 *   server) rm dev-smoke.sqlite3 → migrate --run-syncdb → seed_demo →
 *           FAN_WRITE_THROTTLE_ENABLED=False runserver 127.0.0.1:8000
 *   web)    NEXT_PUBLIC_API_URL=/api API_INTERNAL_URL=http://127.0.0.1:8000/api
 *           API_PROXY_TARGET=http://127.0.0.1:8000 npm run build
 *
 * ⚠️ 함정 2가지(이 리포 고유):
 *  1) next.config가 output:"standalone" → `npm run start`는 클라이언트 JS를 서빙하지 못해
 *     페이지가 하이드레이트되지 않는다(폼은 보이나 클릭·fetch가 죽음). 반드시 standalone 서버로:
 *       cp -r .next/static .next/standalone/.next/static  (public 있으면 함께)
 *       PORT=3000 HOSTNAME=127.0.0.1 API_INTERNAL_URL=… API_PROXY_TARGET=… \
 *         node .next/standalone/server.js
 *  2) NEXT_PUBLIC_API_URL은 빌드 타임 인라인 — Git Bash(MSYS)는 `/api`를 Windows 경로로
 *     변환(→ C:/…/api)해 브라우저가 file:// 로 fetch하게 만든다. 빌드는 PowerShell에서 하거나
 *     MSYS_NO_PATHCONV=1 을 붙여 `/api`가 그대로 인라인되게 한다.
 *
 * 프로젝트 실행 순서(결정성): 저니(journey)는 서버 상태를 변형한다(주문/좋아요/팔로우/계정).
 * 시각 회귀(visual)는 그 상태를 익명으로 읽으므로, 시드가 신선할 때 먼저 찍혀야 베이스라인이
 * 흔들리지 않는다. 그래서 visual을 **별도 프로젝트로 먼저 선언**하고 workers=1로 직렬 실행한다
 * (visual → journey → mobile). 데스크톱 저니 프로젝트가 요구된 "chromium 1280"이다.
 */
export default defineConfig({
  testDir: "./e2e",
  // 단일 외부 서버 + 상태를 변형하는 저니가 있으므로 직렬 실행(레이스·과부하 회피, 순서 보장).
  fullyParallel: false,
  workers: 1,
  // 플래키 내성 — 첫 실패 시 1회 재시도(그 재시도에서만 trace 수집).
  retries: 1,
  forbidOnly: !!process.env.CI,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    {
      // 시각 회귀(1280) — 익명·읽기 전용. 신선한 시드에서 저니보다 먼저 실행(선언 순서 + workers=1).
      name: "visual",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } },
      testMatch: /visual\.spec\.ts$/,
    },
    {
      // 정본 데스크톱 저니(1280) — 14스텝 팬 저니(상태 변형) + 스튜디오 업로드 저니(R12).
      // studio-upload는 저니와 동일 프로젝트에 묶어 같은 워커/순서(visual→journey→mobile)로 실행되게 한다
      // → `npm run e2e` 대상에 포함(실행엔 Django+standalone 기동 필요, config 등록만으로 미실행 방지).
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } },
      testMatch: [/journey\.spec\.ts$/, /studio-upload\.spec\.ts$/],
    },
    {
      // 모바일 스모크 서브셋(375) — 로그인·디스커버리·피드.
      name: "mobile",
      use: {
        browserName: "chromium",
        viewport: { width: 375, height: 812 },
        isMobile: true,
        hasTouch: true,
        deviceScaleFactor: 2,
      },
      testMatch: /mobile-smoke\.spec\.ts$/,
    },
  ],
});
