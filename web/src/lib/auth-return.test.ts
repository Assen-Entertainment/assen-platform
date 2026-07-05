import { describe, it, expect, beforeEach } from "vitest";
import {
  sanitizeNext,
  savePendingAction,
  readPendingAction,
  clearPendingAction,
  DEFAULT_NEXT,
} from "@/lib/auth-return";

describe("sanitizeNext (오픈 리다이렉트 방어)", () => {
  it("동일 오리진 상대경로는 통과한다", () => {
    expect(sanitizeNext("/creator/rabbit")).toBe("/creator/rabbit");
    expect(sanitizeNext("/orders?tab=all")).toBe("/orders?tab=all");
    expect(sanitizeNext("/mypage/subscriptions")).toBe("/mypage/subscriptions");
  });

  it("절대 URL·스킴은 기본값으로 거부한다", () => {
    expect(sanitizeNext("https://evil.com")).toBe(DEFAULT_NEXT);
    expect(sanitizeNext("http://evil.com")).toBe(DEFAULT_NEXT);
    expect(sanitizeNext("javascript:alert(1)")).toBe(DEFAULT_NEXT);
  });

  it("프로토콜 상대(//)·백슬래시 우회를 거부한다", () => {
    expect(sanitizeNext("//evil.com")).toBe(DEFAULT_NEXT);
    expect(sanitizeNext("/\\evil.com")).toBe(DEFAULT_NEXT);
    expect(sanitizeNext("/foo\\bar")).toBe(DEFAULT_NEXT);
  });

  it("제어문자·빈값·비문자는 기본값으로 폴백한다", () => {
    expect(sanitizeNext("/foo\nbar")).toBe(DEFAULT_NEXT);
    expect(sanitizeNext("")).toBe(DEFAULT_NEXT);
    expect(sanitizeNext(null)).toBe(DEFAULT_NEXT);
    expect(sanitizeNext(undefined)).toBe(DEFAULT_NEXT);
  });
});

describe("PendingAction (미완료 액션 브리지)", () => {
  beforeEach(() => sessionStorage.clear());

  it("저장한 팔로우 액션을 그대로 읽는다", () => {
    savePendingAction({ action: "follow", handle: "rabbit", from: "/creator/rabbit" });
    expect(readPendingAction()).toEqual({ action: "follow", handle: "rabbit", from: "/creator/rabbit" });
  });

  it("clear 후에는 null을 반환한다(재실행 멱등)", () => {
    savePendingAction({ action: "follow", handle: "rabbit", from: "/creator/rabbit" });
    clearPendingAction();
    expect(readPendingAction()).toBeNull();
  });

  it("손상된/형태 불일치 값은 null로 무시한다", () => {
    sessionStorage.setItem("assen.pendingAction", "{ not json");
    expect(readPendingAction()).toBeNull();
    sessionStorage.setItem("assen.pendingAction", JSON.stringify({ action: "like", id: "x" }));
    expect(readPendingAction()).toBeNull();
  });
});
