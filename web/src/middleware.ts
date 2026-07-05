import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * 인증 가드(P0) — 보호 경로에 세션 쿠키(assen_access)가 없으면 /login?next=<원경로>로 리다이렉트.
 *
 * ※ 쿠키 존재 ≠ 유효 세션이다(만료·위조 가능). 여기서는 값을 신뢰하지 않고 "존재"만 보는
 *    저비용 1차 가드이며, 실 유효성(만료·권한)의 세밀 판정은 서버 응답 401을 받는 기존
 *    클라이언트 가드(SessionGuard)가 담당한다. httpOnly 쿠키라 Edge에서 값 검증도 불가.
 * ※ Edge 런타임 — Node API 미사용(NextRequest.cookies / NextResponse만 사용).
 */
export function middleware(req: NextRequest) {
  // 쿠키만 존재하면 통과(값 미검증 — 상단 주석 참조).
  if (req.cookies.has("assen_access")) return NextResponse.next();

  const { pathname, search } = req.nextUrl;
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  // 로그인 성공 후 복귀할 원경로(쿼리 포함). login 페이지가 sanitizeNext로 재검증.
  url.searchParams.set("next", pathname + search);
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
