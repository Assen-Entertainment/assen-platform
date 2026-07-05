import * as React from "react";
import { describe, it, expect } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider, useInfiniteQuery } from "@tanstack/react-query";
import {
  getFeedPage,
  getProductsPage,
  getCommentsPage,
  getOrdersPage,
  getNotificationsPage,
  getCreatorsPage,
  type Page,
} from "./index";

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

/**
 * 커서 페이지네이션 소비(R4-W1) — mock 폴백은 단일 페이지(nextCursor 없음)로 회귀 0을 보장하고,
 * 뷰 훅이 쓰는 useInfiniteQuery 계약(queryFn→Page, getNextPageParam=nextCursor, select=평탄화)이
 * fetchNextPage에서 페이지를 올바르게 병합함을 검증한다.
 */
describe("커서 fetcher mock 폴백은 단일 페이지", () => {
  it("nextCursor 없는 단일 페이지를 반환한다(NEXT_PUBLIC_API_URL 미설정)", async () => {
    const feed = await getFeedPage();
    expect(feed.items.length).toBeGreaterThan(0);
    expect(feed.nextCursor).toBeUndefined();
    expect((await getProductsPage()).nextCursor).toBeUndefined();
    expect((await getOrdersPage()).nextCursor).toBeUndefined();
    expect((await getNotificationsPage()).nextCursor).toBeUndefined();
    expect((await getCommentsPage("po1")).nextCursor).toBeUndefined();
    // F6: 크리에이터 커서 페이지도 mock은 단일 페이지(디스커버리 회귀 0).
    const creatorsPage = await getCreatorsPage();
    expect(creatorsPage.items.length).toBeGreaterThan(0);
    expect(creatorsPage.nextCursor).toBeUndefined();
  });

  it("getProductsPage는 creatorId 스코프를 존중한다(mock)", async () => {
    expect((await getProductsPage("c1")).items.length).toBe(4);
    expect((await getProductsPage("c2")).items).toEqual([]);
  });
});

describe("useInfiniteQuery 페이지 병합(뷰 훅 계약)", () => {
  // 프로덕션 훅과 동일 설정: queryFn→Page, getNextPageParam=nextCursor, select=평탄화.
  const PAGES: Record<string, Page<{ id: string }>> = {
    "0": { items: [{ id: "a" }, { id: "b" }], nextCursor: "c1" },
    c1: { items: [{ id: "c" }, { id: "d" }] }, // 마지막 페이지 — nextCursor 없음
  };

  it("fetchNextPage가 다음 페이지를 병합하고 커서 소진 시 hasNextPage=false", async () => {
    const qc = new QueryClient();
    const { result } = renderHook(
      () =>
        useInfiniteQuery({
          queryKey: ["infinite-merge-test"],
          queryFn: ({ pageParam }) => PAGES[pageParam ?? "0"],
          initialPageParam: undefined as string | undefined,
          getNextPageParam: (last) => last.nextCursor ?? undefined,
          select: (data) => data.pages.flatMap((p) => p.items),
        }),
      { wrapper: makeWrapper(qc) },
    );

    // 1페이지: a,b — 다음 커서 존재.
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([{ id: "a" }, { id: "b" }]);
    expect(result.current.hasNextPage).toBe(true);

    await act(async () => {
      await result.current.fetchNextPage();
    });

    // 2페이지 병합: a,b,c,d — 커서 소진 → 더보기 종료.
    await waitFor(() => expect(result.current.data).toHaveLength(4));
    expect(result.current.data).toEqual([{ id: "a" }, { id: "b" }, { id: "c" }, { id: "d" }]);
    expect(result.current.hasNextPage).toBe(false);
  });

  it("initialData(첫 페이지 시드)로 즉시 렌더된다(SSR 하이드레이션)", async () => {
    const qc = new QueryClient();
    const { result } = renderHook(
      () =>
        useInfiniteQuery({
          queryKey: ["infinite-seed-test"],
          queryFn: ({ pageParam }) => PAGES[pageParam ?? "0"],
          initialPageParam: undefined as string | undefined,
          getNextPageParam: (last) => last.nextCursor ?? undefined,
          initialData: { pages: [{ items: [{ id: "seed" }] }], pageParams: [undefined] },
          select: (data) => data.pages.flatMap((p) => p.items),
        }),
      { wrapper: makeWrapper(qc) },
    );

    // initialData가 즉시 노출(로딩 플래시 없음).
    expect(result.current.data).toEqual([{ id: "seed" }]);
  });
});
