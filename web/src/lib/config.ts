/** 런타임 설정 — 환경변수 단일 접근점. (.env.example 참조)
 *  `||` 사용 이유: 컨테이너 빌드처럼 변수가 빈 문자열("")로 주입되는 환경에서
 *  `??`는 폴백을 우회해 `new URL("")`(metadataBase)이 빌드를 깨뜨린다. */
export const config = {
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000",
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "",
  env: process.env.NODE_ENV || "development",
} as const;
