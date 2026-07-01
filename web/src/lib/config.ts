/** 런타임 설정 — 환경변수 단일 접근점. (.env.example 참조) */
export const config = {
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "",
  env: process.env.NODE_ENV ?? "development",
} as const;
