import path from "node:path";
import { fileURLToPath } from "node:url";
import { withSentryConfig } from "@sentry/nextjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  // ESLint 게이트 활성화(빌드 시 lint 실행). 규칙은 eslint.config.mjs.
  // standalone: 컨테이너 패키징(web/Dockerfile)용 자립 산출물(server.js).
  // Vercel 배포와도 무해(무시됨) — 호스팅 최종 결정은 E10 게이트(SDLC 11).
  output: "standalone",
  // next/image 원격 허용 목록(R5-W3 #6) — https 전반 허용은 금지(SSRF/남용 방지), 명시 호스트만.
  // 현재 실 이미지 자산 없음(그라디언트 placeholder) → SmartImage의 next/image 분기는 잠재 인프라.
  // 실 CDN/스토리지 확정 시 아래에 호스트를 추가한다(예: 오브젝트 스토리지·이미지 CDN).
  images: {
    remotePatterns: [
      // 예시(자리표시) — 실 CDN 확정 시 교체:
      // { protocol: "https", hostname: "cdn.assen.example", pathname: "/**" },
      // { protocol: "https", hostname: "**.assen.example", pathname: "/**" },
    ],
  },
  // dev 동일 오리진 프록시 — 브라우저의 `/api/*` 요청을 백엔드로 포워딩한다.
  // 목적: 웹과 API가 같은 오리진처럼 보이게 해 쿠키(SameSite=Lax)가 자연 송신되고
  // CORS가 불필요해진다(SDLC 11 옵션 B 정합). SSR fetch는 프록시를 거치지 않고
  // 서버 전용 API_INTERNAL_URL로 직접 호출한다(client.ts).
  async rewrites() {
    const target = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${target}/api/:path*` }];
  },
  // 기본 보안 헤더(SDLC 11 §4). CSP는 인라인/서드파티 감사 후 별도 도입.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
  // mock 번들 격리(R6-W2C) — 라이브 빌드(NEXT_PUBLIC_API_URL 설정) 전용. USE_API 빌드타임 상수만으로는
  // SWC 미니파이어가 각 함수의 mock 폴백 return문까지 사병 제거하지 못함을 실측(라이브 빌드에도 mock
  // 문자열 잔존) → lib/api/mock/data(실 데이터)를 data.stub(빈 값)으로 물리 치환해 확정적으로 제거한다.
  // USE_API=true 런타임 경로는 이 값을 절대 참조하지 않으므로(if(USE_API) 분기가 먼저 반환) 무해하다.
  webpack(config, { webpack }) {
    if (process.env.NEXT_PUBLIC_API_URL) {
      // 치환 대상 계약: mock 실데이터 모듈(src/lib/api/mock/data.ts)의 import 스펙만 매칭한다.
      // 현재 유일 소비처 index.ts는 상대경로 `./mock/data`를 쓰지만, alias `@/lib/api/mock/data`
      // 임포트가 추가돼도 치환을 놓치지 않도록(→ 라이브 번들 mock 잔존) 두 형태를 모두 커버한다.
      // `$` 앵커로 data.stub/data.test 는 매칭하지 않는다.
      config.plugins.push(
        new webpack.NormalModuleReplacementPlugin(
          /^(?:\.\/mock\/data|@\/lib\/api\/mock\/data)$/,
          (resource) => {
            resource.request = path.resolve(__dirname, "src/lib/api/mock/data.stub.ts");
          },
        ),
      );
      // 스튜디오 재무 mock(정산/애널리틱스 placeholder 금액, ASS-289 #5) — 동일 규율로 물리 치환한다.
      // 유일 런타임 소비처 lib/api/index.ts는 alias `@/lib/studio-mock-finance`를 쓴다(차트는 type-only
      // import → SWC 소거). `$` 앵커로 `.stub` 는 매칭하지 않는다.
      config.plugins.push(
        new webpack.NormalModuleReplacementPlugin(
          /^@\/lib\/studio-mock-finance$/,
          (resource) => {
            resource.request = path.resolve(__dirname, "src/lib/studio-mock-finance.stub.ts");
          },
        ),
      );
    }
    return config;
  },
  // 위 스텁 치환과 짝 — Next의 standalone 파일트레이싱이 실행되지 않는 원본 mock/data.ts 소스를
  // .next/standalone/src로 그대로 복사하는 부작용이 실측 확인됐다(컴파일 산출물엔 미포함·실행 안 됨이나
  // 배포 이미지 파일시스템엔 잔존). 라이브 빌드에서는 트레이싱 대상에서 제외해 이미지에서도 제거한다.
  ...(process.env.NEXT_PUBLIC_API_URL
    ? { outputFileTracingExcludes: { "/**": ["./src/lib/api/mock/data.ts", "./src/lib/studio-mock-finance.ts"] } }
    : {}),
};

// Sentry 배선(ASS-270) — 이 빌드타임 래핑 자체는 항상 적용(자동 계측 삽입·소스맵 후보 생성)되지만,
// 런타임 초기화는 instrumentation.ts / instrumentation-client.ts가 SENTRY_DSN·NEXT_PUBLIC_SENTRY_DSN
// 미설정 시 완전히 스킵한다(서버 observability.py의 init_sentry() no-op-without-DSN 계약과 동일 —
// dev/test/미설정 배포는 네트워크·성능 영향 0). 소스맵 업로드는 SENTRY_AUTH_TOKEN 있을 때만 수행되고,
// 없으면 자동으로 건너뛰며 빌드는 실패하지 않는다(org/project/authToken은 SENTRY_ORG/SENTRY_PROJECT/
// SENTRY_AUTH_TOKEN 환경변수로 자동 폴백 — @sentry/bundler-plugin-core 확인됨).
export default withSentryConfig(nextConfig, {
  sourcemaps: {
    // 토큰 없이 소스맵을 만들어봐야 업로드가 안 되므로(경고만 찍고 스킵) 아예 생성 단계를 건너뛴다.
    disable: !process.env.SENTRY_AUTH_TOKEN,
  },
  // 번들예산 게이트(scripts/check-bundle-budget.mjs, web-ci) 대응 — 클라이언트 번들에 섞여 들어가는
  // SDK 디버그 로깅·Session Replay 관련 코드(Replay integration 미사용)를 트리셰이킹으로 제거한다.
  // tracing(tracesSampleRate)은 요구사항(성능 모니터링 tunable)상 유지 — excludeTracing은 켜지 않는다.
  bundleSizeOptimizations: {
    excludeDebugStatements: true,
    excludeReplayIframe: true,
    excludeReplayShadowDom: true,
    excludeReplayWorker: true,
  },
  // 빌드 로그 소음 억제(플러그인 자체 로그만 — 애플리케이션 빌드 오류/경고는 그대로 노출).
  silent: true,
});
