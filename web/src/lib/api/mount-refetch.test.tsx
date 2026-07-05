import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider, useInfiniteQuery } from "@tanstack/react-query";
import type { Page } from "./index";
import type { Post, Creator } from "./types";

/**
 * M1·F6 회귀 방지 — SSR 배열 시드는 nextCursor가 없어 hasNextPage=false이고, "마운트 refetch가
 * 커서를 채운다"는 설계가 전역 staleTime(60s)에 막혀 더보기가 영구 미노출되던 가짜 green을 해소한다.
 * 실 훅(useFeed/useCreators)이 프로덕션과 동일한 staleTime:60_000 QueryClient에서 initialDataUpdatedAt:0
 * 덕분에 마운트 refetch로 커서 포함 첫 페이지를 받아 hasNextPage=true(더보기 노출)가 되는지 단언한다.
 */

// 실 훅이 리페치 시 커서 포함 첫 페이지를 받도록 fetcher를 모킹(서버 페이지네이션 시뮬).
const { getFeedPageMock, getCreatorsPageMock } = vi.hoisted(() => ({
  getFeedPageMock: vi.fn(),
  getCreatorsPageMock: vi.fn(),
}));
vi.mock("./index", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./index")>();
  return { ...actual, getFeedPage: getFeedPageMock, getCreatorsPage: getCreatorsPageMock };
});

import { useFeed, useCreators } from "./queries";

/** 프로덕션 QueryProvider와 동일한 기본 옵션(staleTime 60s)의 래퍼 — 가짜 green의 핵심 조건. */
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

describe("M1: SSR 시드 무한 리스트 마운트 refetch(프로덕션 staleTime 60s)", () => {
  it("useFeed: 시드는 hasNextPage=false지만 마운트 refetch가 커서 페이지로 교체해 더보기가 노출된다", async () => {
    getFeedPageMock.mockResolvedValue({ items: [post("po1")], nextCursor: "cursor-2" });
    const { result } = renderHook(() => useFeed([post("po1")]), { wrapper: prodWrapper() });
    // 시드 즉시 렌더(로딩 플래시 없음) — 커서가 없어 더보기 미노출.
    expect(result.current.data).toEqual([post("po1")]);
    expect(result.current.hasNextPage).toBe(false);
    // initialDataUpdatedAt:0 → 즉시 stale → staleTime 60s에도 마운트 refetch가 nextCursor를 채운다.
    await waitFor(() => expect(result.current.hasNextPage).toBe(true));
    expect(getFeedPageMock).toHaveBeenCalled();
  });

  it("가짜 green 가드: initialDataUpdatedAt 없이 staleTime 60s면 마운트 refetch가 없어 hasNextPage=false로 고착된다(구 버그 재현)", async () => {
    const queryFn = vi.fn().mockResolvedValue({ items: [post("x")], nextCursor: "c2" });
    const { result } = renderHook(
      () =>
        useInfiniteQuery({
          queryKey: ["m1-fake-green-guard"],
          queryFn,
          initialPageParam: undefined as string | undefined,
          getNextPageParam: (last: Page<Post>) => last.nextCursor ?? undefined,
          initialData: { pages: [{ items: [post("seed")] }], pageParams: [undefined] },
          // ★initialDataUpdatedAt 부재 → 시드가 fresh로 간주 → 마운트 refetch 없음.
          select: (d) => d.pages.flatMap((p) => p.items),
        }),
      { wrapper: prodWrapper() },
    );
    // 시드가 fresh → refetch 미발생 → 커서 못 채움 → 더보기 영구 미노출.
    await new Promise((r) => setTimeout(r, 60));
    expect(queryFn).not.toHaveBeenCalled();
    expect(result.current.hasNextPage).toBe(false);
  });
});

describe("F6: useCreators 무한 쿼리(디스커버리 21번째+ 도달)", () => {
  it("SSR 시드는 더보기 미노출이지만 마운트 refetch가 커서 페이지로 교체해 더보기가 노출된다", async () => {
    getCreatorsPageMock.mockResolvedValue({ items: [creator("c1")], nextCursor: "cursor-2" });
    const { result } = renderHook(() => useCreators([creator("c1")]), { wrapper: prodWrapper() });
    // select 평탄화 → 소비처(discovery-view)는 Creator[] 형태 그대로 소비(무변경).
    expect(result.current.data).toEqual([creator("c1")]);
    expect(result.current.hasNextPage).toBe(false);
    await waitFor(() => expect(result.current.hasNextPage).toBe(true));
    expect(getCreatorsPageMock).toHaveBeenCalled();
  });
});
