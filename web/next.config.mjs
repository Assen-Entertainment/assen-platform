/** @type {import('next').NextConfig} */
const nextConfig = {
  // ESLint 게이트 활성화(빌드 시 lint 실행). 규칙은 eslint.config.mjs.
  // standalone: 컨테이너 패키징(web/Dockerfile)용 자립 산출물(server.js).
  // Vercel 배포와도 무해(무시됨) — 호스팅 최종 결정은 E10 게이트(SDLC 11).
  output: "standalone",
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
