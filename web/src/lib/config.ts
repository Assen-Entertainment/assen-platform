/** 런타임 설정 — 환경변수 단일 접근점. (.env.example 참조)
 *  `||` 사용 이유: 컨테이너 빌드처럼 변수가 빈 문자열("")로 주입되는 환경에서
 *  `??`는 폴백을 우회해 `new URL("")`(metadataBase)이 빌드를 깨뜨린다.
 *
 *  apiUrl: 비면 lib/api가 in-file mock으로 폴백(USE_API=false — 빌드/CI/오프라인 개발).
 *  라이브 백엔드 연동 시 값 설정(USE_API=true). dev 프록시 모드에선 동일 오리진 상대경로
 *  `/api` 권장(next.config rewrites가 백엔드로 포워딩 — 쿠키 Lax 자연 송신). SSR 절대 URL은
 *  서버 전용 `API_INTERNAL_URL`이 담당(client.ts). */
export const config = {
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000",
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "",
  env: process.env.NODE_ENV || "development",
} as const;
