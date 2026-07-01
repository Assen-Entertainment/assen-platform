import * as React from "react";
import { describe, it, expect } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useToggleLike, useAddComment, qk } from "./queries";
import type { Post, Comment } from "./types";

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
