import * as React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  track,
  registerCollector,
  resetCollectors,
  createConsoleCollector,
  type AnalyticsCollector,
  type AnalyticsEvent,
} from "./index";
import { useToggleFollow, useReport, useAddComment, qk } from "@/lib/api/queries";
import type { Creator, Comment, Post } from "@/lib/api/types";

/** 이벤트를 배열에 모으는 테스트 수집기(발화 검증용). */
function makeRecorder(): { events: AnalyticsEvent[]; collector: AnalyticsCollector } {
  const events: AnalyticsEvent[] = [];
  return { events, collector: { collect: (e) => events.push(e) } };
}

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

beforeEach(() => {
  resetCollectors();
});

describe("analytics facade — 수집기 등록/발화", () => {
  it("수집기가 없으면 no-op(예외 없음)", () => {
    expect(() => track("page_view", { path: "/feed" })).not.toThrow();
  });

  it("등록된 수집기에 { name, props }를 정확히 1회 전달한다", () => {
    const { events, collector } = makeRecorder();
    registerCollector(collector);

    track("login_completed", { method: "otp" });

    expect(events).toEqual([{ name: "login_completed", props: { method: "otp" } }]);
  });

  it("다중 수집기 전부에 전달한다", () => {
    const a = makeRecorder();
    const b = makeRecorder();
    registerCollector(a.collector);
    registerCollector(b.collector);

    track("follow_toggled", { following: true });

    expect(a.events).toHaveLength(1);
    expect(b.events).toHaveLength(1);
  });

  it("해제 함수 호출 후에는 발화되지 않는다", () => {
    const { events, collector } = makeRecorder();
    const unregister = registerCollector(collector);

    track("post_liked", { liked: true });
    unregister();
    track("post_liked", { liked: false });

    expect(events).toEqual([{ name: "post_liked", props: { liked: true } }]);
  });

  it("한 수집기가 던져도 다른 수집기·앱 흐름을 막지 않는다", () => {
    const bad: AnalyticsCollector = {
      collect: () => {
        throw new Error("boom");
      },
    };
    const { events, collector } = makeRecorder();
    registerCollector(bad);
    registerCollector(collector);

    expect(() => track("search_performed", { queryLength: 3 })).not.toThrow();
    expect(events).toHaveLength(1);
  });

  it("console 수집기는 console.debug로 이벤트를 남긴다", () => {
    const spy = vi.spyOn(console, "debug").mockImplementation(() => {});
    registerCollector(createConsoleCollector());

    track("block_toggled", { blocked: true });

    expect(spy).toHaveBeenCalledWith("[analytics]", "block_toggled", { blocked: true });
    spy.mockRestore();
  });
});

describe("analytics 이벤트 페이로드 — PII 부재 계약", () => {
  // 각 이벤트의 대표 페이로드(정의된 전체 이벤트를 1건씩 커버).
  const SAMPLES: AnalyticsEvent[] = [
    { name: "page_view", props: { path: "/creator/stellar" } },
    { name: "signup_completed", props: { method: "otp" } },
    { name: "login_completed", props: { method: "mock" } },
    { name: "follow_toggled", props: { following: true } },
    { name: "post_liked", props: { liked: false } },
    { name: "comment_created", props: { postId: "po1" } },
    { name: "order_created", props: { productId: "p1", qty: 2 } },
    { name: "subscription_started", props: { tierId: "t2" } },
    { name: "tier_changed", props: { tierId: "t3" } },
    { name: "search_performed", props: { queryLength: 4 } },
    { name: "report_submitted", props: { reportType: "spam" } },
    { name: "block_toggled", props: { blocked: true } },
  ];

  // PII를 시사하는 키 이름(전화·이름·주소·이메일·닉네임·서술 등) — payload에 등장 금지.
  const FORBIDDEN_KEY = /phone|name|address|email|nickname|narrative|recipient|postal/i;

  it("모든 이벤트 payload는 원시값(string/number/boolean)만 담는다", () => {
    for (const e of SAMPLES) {
      for (const v of Object.values(e.props)) {
        expect(["string", "number", "boolean"]).toContain(typeof v);
      }
    }
  });

  it("payload 키에 PII를 시사하는 자유 필드가 없다", () => {
    for (const e of SAMPLES) {
      for (const k of Object.keys(e.props)) {
        expect(FORBIDDEN_KEY.test(k)).toBe(false);
      }
    }
  });

  it("payload 값에 전화번호/이메일 형태 문자열이 없다", () => {
    const PHONE = /\d{2,4}-?\d{3,4}-?\d{4}/;
    const EMAIL = /@/;
    for (const e of SAMPLES) {
      for (const v of Object.values(e.props)) {
        if (typeof v === "string") {
          expect(PHONE.test(v)).toBe(false);
          expect(EMAIL.test(v)).toBe(false);
        }
      }
    }
  });
});

describe("계측 배선 — 뮤테이션당 단일 발화(중복 금지)", () => {
  const creator: Creator = { id: "c1", name: "별빛", handle: "stellar", followers: 10, following: false };

  it("useToggleFollow 성공 시 follow_toggled를 정확히 1회 발화한다", async () => {
    const { events, collector } = makeRecorder();
    registerCollector(collector);
    const qc = new QueryClient();
    qc.setQueryData(qk.creator("stellar"), creator);

    const { result } = renderHook(() => useToggleFollow("stellar"), { wrapper: makeWrapper(qc) });
    act(() => {
      result.current.mutate(true);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const follows = events.filter((e) => e.name === "follow_toggled");
    expect(follows).toEqual([{ name: "follow_toggled", props: { following: true } }]);
  });

  it("useReport 성공 시 report_submitted를 1회 발화하고 서술(narrative)은 담지 않는다", async () => {
    const { events, collector } = makeRecorder();
    registerCollector(collector);
    const qc = new QueryClient();

    const { result } = renderHook(() => useReport(), { wrapper: makeWrapper(qc) });
    act(() => {
      result.current.mutate({ reportType: "spam", narrative: "민감한 서술 텍스트" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const reports = events.filter((e) => e.name === "report_submitted");
    expect(reports).toHaveLength(1);
    // 유형 코드만 — 서술은 payload에 없다(PII 차단).
    expect(reports[0].props).toEqual({ reportType: "spam" });
    expect(JSON.stringify(reports[0].props)).not.toContain("민감한 서술");
  });

  it("useAddComment 성공 시 comment_created를 1회 발화한다(본문 미포함)", async () => {
    const { events, collector } = makeRecorder();
    registerCollector(collector);
    const qc = new QueryClient();
    const basePost: Post = { id: "po1", creatorId: "c1", creatorName: "테스트", likeCount: 0, commentCount: 0, liked: false };
    qc.setQueryData(qk.comments("po1"), [] as Comment[]);
    qc.setQueryData(qk.post("po1"), basePost);

    const { result } = renderHook(() => useAddComment("po1"), { wrapper: makeWrapper(qc) });
    act(() => {
      result.current.mutate("좋은 작품이에요");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const comments = events.filter((e) => e.name === "comment_created");
    expect(comments).toEqual([{ name: "comment_created", props: { postId: "po1" } }]);
    expect(JSON.stringify(comments[0].props)).not.toContain("좋은 작품");
  });
});
