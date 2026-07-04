import * as React from "react";
import { describe, it, expect } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useToggleLike, useAddComment, useBlockCreator, useUnblockCreator, useStudioStats, qk } from "./queries";
import type { Post, Comment, Creator, BlockedCreator, StudioStats } from "./types";

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

const basePost: Post = {
  id: "po1",
  creatorId: "c1",
  creatorName: "테스트",
  likeCount: 10,
  commentCount: 0,
  liked: false,
};

describe("useToggleLike (optimistic)", () => {
  it("좋아요 시 post·feed 캐시를 즉시 갱신한다", async () => {
    const qc = new QueryClient();
    qc.setQueryData(qk.post("po1"), basePost);
    qc.setQueryData(qk.feed, [basePost]);

    const { result } = renderHook(() => useToggleLike(), { wrapper: makeWrapper(qc) });
    act(() => {
      result.current.mutate({ id: "po1", next: true });
    });

    await waitFor(() => {
      const p = qc.getQueryData<Post>(qk.post("po1"));
      expect(p?.liked).toBe(true);
      expect(p?.likeCount).toBe(11);
      const feed = qc.getQueryData<Post[]>(qk.feed);
      expect(feed?.[0].liked).toBe(true);
      expect(feed?.[0].likeCount).toBe(11);
    });
  });

  it("좋아요 취소 시 카운트를 1 감소시킨다", async () => {
    const qc = new QueryClient();
    qc.setQueryData(qk.post("po1"), { ...basePost, liked: true, likeCount: 11 });

    const { result } = renderHook(() => useToggleLike(), { wrapper: makeWrapper(qc) });
    act(() => {
      result.current.mutate({ id: "po1", next: false });
    });

    await waitFor(() => {
      const p = qc.getQueryData<Post>(qk.post("po1"));
      expect(p?.liked).toBe(false);
      expect(p?.likeCount).toBe(10);
    });
  });

  it("이미 같은 상태면 카운트를 중복 반영하지 않는다(멱등)", async () => {
    const qc = new QueryClient();
    qc.setQueryData(qk.post("po1"), { ...basePost, liked: true, likeCount: 11 });

    const { result } = renderHook(() => useToggleLike(), { wrapper: makeWrapper(qc) });
    act(() => {
      result.current.mutate({ id: "po1", next: true });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const p = qc.getQueryData<Post>(qk.post("po1"));
    expect(p?.liked).toBe(true);
    expect(p?.likeCount).toBe(11);
  });

  it("likeCount를 0 미만으로 내리지 않는다(클램프)", async () => {
    const qc = new QueryClient();
    qc.setQueryData(qk.post("po1"), { ...basePost, liked: true, likeCount: 0 });

    const { result } = renderHook(() => useToggleLike(), { wrapper: makeWrapper(qc) });
    act(() => {
      result.current.mutate({ id: "po1", next: false });
    });

    await waitFor(() => {
      const p = qc.getQueryData<Post>(qk.post("po1"));
      expect(p?.liked).toBe(false);
      expect(p?.likeCount).toBe(0);
    });
  });

  it("포스트 목록(['posts', …]) 캐시도 함께 갱신한다(프로필 통일)", async () => {
    const qc = new QueryClient();
    qc.setQueryData(qk.post("po1"), basePost);
    qc.setQueryData(qk.posts("c1"), [basePost]);

    const { result } = renderHook(() => useToggleLike(), { wrapper: makeWrapper(qc) });
    act(() => {
      result.current.mutate({ id: "po1", next: true });
    });

    await waitFor(() => {
      const list = qc.getQueryData<Post[]>(qk.posts("c1"));
      expect(list?.[0].liked).toBe(true);
      expect(list?.[0].likeCount).toBe(11);
    });
  });
});

describe("useBlockCreator (optimistic)", () => {
  it("차단 시 크리에이터 blocked=true·following=false로 갱신하고 피드에서 해당 크리에이터 포스트를 제거한다", async () => {
    const qc = new QueryClient();
    const creator: Creator = { id: "c1", name: "별빛", handle: "stellar", followers: 10, following: true };
    qc.setQueryData(qk.creator("stellar"), creator);
    // 피드: c1 포스트 + c2 포스트 → 차단 후 c1만 사라져야 한다.
    qc.setQueryData(qk.feed, [basePost, { ...basePost, id: "po2", creatorId: "c2" }]);

    const { result } = renderHook(() => useBlockCreator(), { wrapper: makeWrapper(qc) });
    act(() => {
      result.current.mutate({ creatorId: "c1", handle: "stellar" });
    });

    await waitFor(() => {
      const c = qc.getQueryData<Creator>(qk.creator("stellar"));
      expect(c?.blocked).toBe(true);
      expect(c?.following).toBe(false); // 자동 언팔로우
      const feed = qc.getQueryData<Post[]>(qk.feed);
      expect(feed?.map((p) => p.id)).toEqual(["po2"]);
    });
  });
});

describe("useUnblockCreator (optimistic)", () => {
  it("해제 시 차단 목록에서 제거하고 크리에이터 blocked=false로 갱신한다", async () => {
    const qc = new QueryClient();
    qc.setQueryData<Creator>(qk.creator("stellar"), {
      id: "c1",
      name: "별빛",
      handle: "stellar",
      followers: 10,
      blocked: true,
    });
    qc.setQueryData<BlockedCreator[]>(qk.blocks, [{ creatorId: "c1", name: "별빛", handle: "stellar" }]);

    const { result } = renderHook(() => useUnblockCreator(), { wrapper: makeWrapper(qc) });
    act(() => {
      result.current.mutate({ creatorId: "c1", handle: "stellar" });
    });

    await waitFor(() => {
      const c = qc.getQueryData<Creator>(qk.creator("stellar"));
      expect(c?.blocked).toBe(false);
      expect(qc.getQueryData<BlockedCreator[]>(qk.blocks)).toEqual([]);
    });
  });
});

describe("useStudioStats", () => {
  it("스튜디오 실 카운트를 노출한다(mock 폴백)", async () => {
    const qc = new QueryClient();
    const { result } = renderHook(() => useStudioStats(), { wrapper: makeWrapper(qc) });
    await waitFor(() => expect(result.current.data).toBeTruthy());
    const stats = result.current.data as StudioStats;
    // 팔로워는 기존 대시보드 수치와 일관, 판매중은 전체 상품의 부분집합.
    expect(stats.followers).toBe(12400);
    expect(stats.productsSelling).toBeLessThanOrEqual(stats.products);
    // 금액/수익 필드는 없다(정산 게이트).
    expect(stats).not.toHaveProperty("revenue");
  });

  it("시드된 null(비크리에이터/비로그인)을 그대로 노출한다(카운트 날조 안 함)", () => {
    const qc = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity } } });
    qc.setQueryData<StudioStats | null>(qk.studioStats, null);
    const { result } = renderHook(() => useStudioStats(), { wrapper: makeWrapper(qc) });
    expect(result.current.data).toBeNull();
  });
});

describe("useAddComment (optimistic)", () => {
  it("댓글을 목록에 즉시 추가하고 commentCount 를 올린다", async () => {
    const qc = new QueryClient();
    qc.setQueryData(qk.comments("po1"), [] as Comment[]);
    qc.setQueryData(qk.post("po1"), { ...basePost, commentCount: 0 });

    const { result } = renderHook(() => useAddComment("po1"), { wrapper: makeWrapper(qc) });
    act(() => {
      result.current.mutate("좋은 작품이에요");
    });

    await waitFor(() => {
      const list = qc.getQueryData<Comment[]>(qk.comments("po1"));
      expect(list?.length).toBe(1);
      expect(list?.[0].body).toBe("좋은 작품이에요");
      const p = qc.getQueryData<Post>(qk.post("po1"));
      expect(p?.commentCount).toBe(1);
    });
  });
});
