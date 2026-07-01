"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCreators, getCreator, getProducts, getMembershipTiers, getPosts, getPost, getComments } from "./index";
import type { Creator, Post, Comment } from "./types";

/** 네트워크 지연 시뮬레이션(목업). 실 API 연동 시 제거. */
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** 쿼리 키 */
export const qk = {
  creators: ["creators"] as const,
  creator: (handle: string) => ["creator", handle] as const,
  products: ["products"] as const,
  tiers: (id?: string) => ["tiers", id ?? "all"] as const,
  posts: (id?: string) => ["posts", id ?? "all"] as const,
  feed: ["feed"] as const,
  post: (id: string) => ["post", id] as const,
  comments: (postId: string) => ["comments", postId] as const,
};

export function useCreators() {
  return useQuery({ queryKey: qk.creators, queryFn: getCreators });
}
export function useCreator(handle: string, initialData?: Creator) {
  return useQuery({ queryKey: qk.creator(handle), queryFn: () => getCreator(handle), initialData });
}
export function useProducts() {
  return useQuery({ queryKey: qk.products, queryFn: () => getProducts() });
}
export function useMembershipTiers(id?: string) {
  return useQuery({ queryKey: qk.tiers(id), queryFn: () => getMembershipTiers(id) });
}
export function usePosts(id?: string) {
  return useQuery({ queryKey: qk.posts(id), queryFn: () => getPosts(id) });
}
/** 팔로잉 피드(전체 포스트). 서버 initialData 하이드레이션. */
export function useFeed(initialData?: Post[]) {
  return useQuery({ queryKey: qk.feed, queryFn: () => getPosts(), initialData });
}
export function usePost(id: string, initialData?: Post) {
  return useQuery({ queryKey: qk.post(id), queryFn: () => getPost(id), initialData });
}
export function useComments(postId: string, initialData?: Comment[]) {
  return useQuery({ queryKey: qk.comments(postId), queryFn: () => getComments(postId), initialData });
}

/** 팔로우 토글 — 낙관적 업데이트(캐시 즉시 반영, 실패 시 롤백). ※목업: 실 API 미연동. */
export function useToggleFollow(handle: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (next: boolean) => {
      await sleep(200); // 네트워크 시뮬레이션
      return next;
    },
    onMutate: async (next: boolean) => {
      await qc.cancelQueries({ queryKey: qk.creator(handle) });
      const prev = qc.getQueryData<Creator>(qk.creator(handle));
      qc.setQueryData<Creator | undefined>(qk.creator(handle), (c) => (c ? { ...c, following: next } : c));
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.creator(handle), ctx.prev);
    },
  });
}

/**
 * 좋아요 토글 — 낙관적. 포스트 상세(qk.post)와 피드(qk.feed) 캐시를 동시 갱신 후
 * 실패 시 둘 다 롤백. ※목업: 실 API 미연동.
 */
export function useToggleLike() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { id: string; next: boolean }) => {
      await sleep(150);
      return v;
    },
    onMutate: async ({ id, next }: { id: string; next: boolean }) => {
      await qc.cancelQueries({ queryKey: qk.post(id) });
      await qc.cancelQueries({ queryKey: qk.feed });
      const prevPost = qc.getQueryData<Post>(qk.post(id));
      const prevFeed = qc.getQueryData<Post[]>(qk.feed);
      const apply = (p: Post): Post =>
        p.id === id ? { ...p, liked: next, likeCount: p.likeCount + (next ? 1 : -1) } : p;
      qc.setQueryData<Post | undefined>(qk.post(id), (p) => (p ? apply(p) : p));
      qc.setQueryData<Post[] | undefined>(qk.feed, (list) => list?.map(apply));
      return { prevPost, prevFeed, id };
    },
    onError: (_e, _v, ctx) => {
      if (!ctx) return;
      if (ctx.prevPost) qc.setQueryData(qk.post(ctx.id), ctx.prevPost);
      if (ctx.prevFeed) qc.setQueryData(qk.feed, ctx.prevFeed);
    },
  });
}

/**
 * 댓글 작성 — 낙관적. 댓글 목록(qk.comments)에 즉시 추가 + 포스트 commentCount 증가.
 * 실패 시 목록 롤백. ※목업: 실 API 미연동.
 */
export function useAddComment(postId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: string) => {
      await sleep(150);
      return body;
    },
    onMutate: async (body: string) => {
      await qc.cancelQueries({ queryKey: qk.comments(postId) });
      const prev = qc.getQueryData<Comment[]>(qk.comments(postId));
      const optimistic: Comment = {
        id: `tmp-${prev?.length ?? 0}`,
        postId,
        author: "나",
        authorFallback: "나",
        body,
        createdAt: "방금",
      };
      qc.setQueryData<Comment[]>(qk.comments(postId), (list) => [...(list ?? []), optimistic]);
      qc.setQueryData<Post | undefined>(qk.post(postId), (p) =>
        p ? { ...p, commentCount: p.commentCount + 1 } : p,
      );
      return { prev, prevCount: prev?.length ?? 0 };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.comments(postId), ctx.prev);
    },
  });
}
