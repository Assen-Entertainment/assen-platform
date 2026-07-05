import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * mock 모드(NEXT_PUBLIC_API_URL 미설정) 여부 — Edge에서 빌드타임 인라인되는 상수.
 * mock 로그인은 httpOnly 쿠키(assen_access)를 심지 않으므로, 쿠키 가드를 켜두면 로그인해도
 * 보호 라우트가 영구 차단되어 무한 로그인 루프(login→push(next)→다시 /login)가 발생한다.
 *
 * ⚠ 불변식: MOCK_MODE는 빌드타임에 인라인된다(런타임 env 주입으로 되돌릴 수 없다). 따라서
 * NEXT_PUBLIC_API_URL 없이 빌드한 이미지는 이 인증 가드가 조용히 영구 비활성이다. 배포 이미지는
 * web/Dockerfile의 프로드 가드가 NEXT_PUBLIC_API_URL을 강제한다(누락 시 이미지 빌드 실패).
 * mock 빌드 산출물(NEXT_PUBLIC_API_URL 없이 빌드)은 절대 배포하지 말 것.
 */
const MOCK_MODE = !process.env.NEXT_PUBLIC_API_URL;

/**
 * 보호 경로 접근 판정(순수 — 단위 테스트 대상).
 * @returns 로그인 후 복귀할 원경로(리다이렉트 필요) 또는 null(가드 통과).
 *
 * - mock 모드(실 API 미설정): 항상 통과 → 클라이언트 SessionGuard만 담당(쿠키 가드 비활성).
 * - 실 API 모드: 세션 쿠키(assen_access) "존재"만 보는 저비용 1차 가드(값 미검증 — httpOnly라
 *   Edge에서 검증 불가). 실 유효성(만료·권한)은 서버 401을 받는 SessionGuard가 세밀 판정한다.
 */
export function guardRedirectTarget(opts: {
  mockMode: boolean;
  hasSession: boolean;
  pathname: string;
  search: string;
}): string | null {
  if (opts.mockMode) return null;
  if (opts.hasSession) return null;
  return opts.pathname + opts.search;
}

/**
 * 인증 가드(P0) — 실 API 모드에서 보호 경로에 세션 쿠키가 없으면 /login?next=<원경로>로 리다이렉트.
 * ※ Edge 런타임 — Node API 미사용(NextRequest.cookies / NextResponse만 사용).
 */
export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  const next = guardRedirectTarget({
    mockMode: MOCK_MODE,
    hasSession: req.cookies.has("assen_access"),
    pathname,
    search,
  });
  if (next === null) return NextResponse.next();

  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  // 로그인 성공 후 복귀할 원경로(쿼리 포함). login 페이지가 sanitizeNext로 재검증.
  url.searchParams.set("next", next);
  return NextResponse.redirect(url);
}

// 보호 경로만 스코프 한정(정적 자산·/api·공개 경로 제외). base·하위 모두 매칭.
export const config = {
  matcher: [
    "/orders",
    "/orders/:path*",
    "/settings",
    "/settings/:path*",
    "/studio",
    "/studio/:path*",
    "/mypage",
    "/mypage/:path*",
  ],
};
