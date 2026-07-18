import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Post, Creator } from "./types";

/**
 * 이중 페치 제거(R5-W2D) — SSR가 Page형(items+nextCursor) 시드를 주면 nextCursor가 처음부터 있어
 * hasNextPage가 마운트 즉시 정확하고, initialDataUpdatedAt:0 없이도 전역 staleTime(60s)이 시드를
 * 신선으로 간주해 마운트 refetch(이중 페치)가 발생하지 않는다. 구 계약(배열 시드 → 강제 stale →
 * 마운트마다 첫 페이지 재요청)의 회귀를 이 테스트가 방지한다.
 */

// fetcher가 호출되면 안 됨을 단언하기 위해 mock으로 감지(호출 시 커서 페이지 반환).
const { getFeedPageMock, getCreatorsPageMock } = vi.hoisted(() => ({
  getFeedPageMock: vi.fn(),
  getCreatorsPageMock: vi.fn(),
}));
vi.mock("./index", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./index")>();
  return { ...actual, getFeedPage: getFeedPageMock, getCreatorsPage: getCreatorsPageMock };
});

import { useFeed, useCreators } from "./queries";

/** 프로덕션 QueryProvider와 동일한 기본 옵션(staleTime 60s)의 래퍼 — 이중 페치 판정의 핵심 조건. */
function prodWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

const post = (id: string): Post => ({ id, creatorId: "c1", creatorName: "t", likeCount: 0, commentCount: 0, liked: false });
const creator = (id: string): Creator => ({ id, name: id, handle: id, followers: 0 });

beforeEach(() => {
  getFeedPageMock.mockReset();
  getCreatorsPageMock.mockReset();
});

describe("W2D: Page 시드 → 이중 페치 없이 hasNextPage 정확", () => {
  it("useFeed: nextCursor 포함 Page 시드는 마운트 즉시 hasNextPage=true이고 mount refetch가 없다", async () => {
    getFeedPageMock.mockResolvedValue({ items: [post("po1")], nextCursor: "cursor-2" });
    const { result } = renderHook(() => useFeed({ items: [post("po1")], nextCursor: "cursor-1" }), {
      wrapper: prodWrapper(),
    });
    // 시드 즉시 렌더 + nextCursor가 있어 더보기 노출(마운트 refetch를 기다리지 않는다).
    expect(result.current.data).toEqual([post("po1")]);
    expect(result.current.hasNextPage).toBe(true);
    // 신선 60s 캐시 존중 → fetcher 미호출(이중 페치 소멸).
    await new Promise((r) => setTimeout(r, 60));
    expect(getFeedPageMock).not.toHaveBeenCalled();
    expect(result.current.hasNextPage).toBe(true);
  });

  it("useFeed: mock 단일 페이지 시드(nextCursor 없음)는 hasNextPage=false이고 refetch도 없다", async () => {
    const { result } = renderHook(() => useFeed({ items: [post("po1")] }), { wrapper: prodWrapper() });
    expect(result.current.data).toEqual([post("po1")]);
    expect(result.current.hasNextPage).toBe(false);
    await new Promise((r) => setTimeout(r, 60));
    expect(getFeedPageMock).not.toHaveBeenCalled();
  });

  it("useCreators: nextCursor 포함 Page 시드는 마운트 즉시 hasNextPage=true이고 mount refetch가 없다", async () => {
    getCreatorsPageMock.mockResolvedValue({ items: [creator("c1")], nextCursor: "cursor-2" });
    const { result } = renderHook(() => useCreators({ items: [creator("c1")], nextCursor: "cursor-1" }), {
      wrapper: prodWrapper(),
    });
    // select 평탄화 → 소비처(discovery-view)는 Creator[] 형태 그대로 소비(무변경).
    expect(result.current.data).toEqual([creator("c1")]);
    expect(result.current.hasNextPage).toBe(true);
    await new Promise((r) => setTimeout(r, 60));
    expect(getCreatorsPageMock).not.toHaveBeenCalled();
  });
});

describe("W2D: 시드 소진 후 fetchNextPage는 정상 동작(커서 이어받기)", () => {
  it("useFeed: 시드의 nextCursor로 다음 페이지를 이어 로드하고 커서 소진 시 종료한다", async () => {
    getFeedPageMock.mockResolvedValue({ items: [post("po2")] }); // 마지막 페이지(nextCursor 없음)
    const { result } = renderHook(() => useFeed({ items: [post("po1")], nextCursor: "cursor-1" }), {
      wrapper: prodWrapper(),
    });
    expect(result.current.hasNextPage).toBe(true);
    await result.current.fetchNextPage();
    await waitFor(() => expect(result.current.data).toEqual([post("po1"), post("po2")]));
    expect(result.current.hasNextPage).toBe(false);
    expect(getFeedPageMock).toHaveBeenCalledWith("cursor-1");
  });
});
