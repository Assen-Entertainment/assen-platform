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
};

export default nextConfig;
