import { describe, it, expect } from "vitest";
import { guardRedirectTarget } from "./middleware";

/**
 * F-C — 미들웨어 가드 판정(순수 함수). mock 모드(NEXT_PUBLIC_API_URL 미설정)에서는
 * 쿠키가 없어도 통과해야 한다(mock 로그인은 쿠키를 안 심어 무한 로그인 루프가 나던 결함).
 */
describe("guardRedirectTarget", () => {
  it("mock 모드에서는 쿠키가 없어도 통과한다(무한 로그인 루프 방지)", () => {
    expect(
      guardRedirectTarget({ mockMode: true, hasSession: false, pathname: "/studio", search: "" }),
    ).toBeNull();
    // 쿠키 유무와 무관하게 통과.
    expect(
      guardRedirectTarget({ mockMode: true, hasSession: true, pathname: "/mypage", search: "?tab=x" }),
    ).toBeNull();
  });

  it("실 API 모드 + 세션 쿠키 있으면 통과한다", () => {
    expect(
      guardRedirectTarget({ mockMode: false, hasSession: true, pathname: "/studio", search: "" }),
    ).toBeNull();
  });

  it("실 API 모드 + 세션 쿠키 없으면 원경로(쿼리 포함)를 반환한다", () => {
    expect(
      guardRedirectTarget({ mockMode: false, hasSession: false, pathname: "/orders", search: "" }),
    ).toBe("/orders");
    expect(
      guardRedirectTarget({
        mockMode: false,
        hasSession: false,
        pathname: "/mypage/subscriptions",
        search: "?tab=all",
      }),
    ).toBe("/mypage/subscriptions?tab=all");
  });
});
