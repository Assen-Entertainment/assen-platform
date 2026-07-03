"use client";
import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import {
  getCreators,
  getCreator,
  getProducts,
  getProduct,
  getMembershipTiers,
  getPosts,
  getPost,
  getComments,
  getFeed,
  getSearch,
  getOrders,
  getOrder,
  getNotifications,
  getSubscriptions,
} from "./index";
import type { Creator, Post, Comment, Product, Order, Notification, Subscription } from "./types";

/** 네트워크 지연 시뮬레이션(목업). 실 API 연동 시 제거. */
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** 쿼리 키 */
export const qk = {
  creators: ["creators"] as const,
  creator: (handle: string) => ["creator", handle] as const,
  products: (creatorId?: string) => ["products", creatorId ?? "all"] as const,
  product: (id: string) => ["product", id] as const,
  tiers: (id?: string) => ["tiers", id ?? "all"] as const,
  posts: (id?: string) => ["posts", id ?? "all"] as const,
  feed: ["feed"] as const,
  post: (id: string) => ["post", id] as const,
  comments: (postId: string) => ["comments", postId] as const,
  search: (q: string) => ["search", q] as const,
  orders: ["orders"] as const,
  order: (id: string) => ["order", id] as const,
  notifications: ["notifications"] as const,
  subscriptions: ["subscriptions"] as const,
};

export function useCreators(initialData?: Creator[]) {
  return useQuery({ queryKey: qk.creators, queryFn: getCreators, initialData });
}
export function useCreator(handle: string, initialData?: Creator) {
  return useQuery({ queryKey: qk.creator(handle), queryFn: () => getCreator(handle), initialData });
}
export function useProducts(creatorId?: string, initialData?: Product[]) {
  return useQuery({ queryKey: qk.products(creatorId), queryFn: () => getProducts(creatorId), initialData });
}
export function useMembershipTiers(id?: string) {
  return useQuery({ queryKey: qk.tiers(id), queryFn: () => getMembershipTiers(id) });
}
export function usePosts(id?: string, initialData?: Post[]) {
  return useQuery({ queryKey: qk.posts(id), queryFn: () => getPosts(id), initialData });
}
/** 피드 — B2 `/feed` 소비(B3 개인화 배선 지점). 서버 initialData 하이드레이션. */
export function useFeed(initialData?: Post[]) {
  return useQuery({ queryKey: qk.feed, queryFn: getFeed, initialData });
}
/** 검색 — B2 `/search?q=` 소비. 빈 질의는 비활성, 타이핑 중 직전 결과 유지. */
export function useSearch(q: string) {
  return useQuery({
    queryKey: qk.search(q),
    queryFn: () => getSearch(q),
    enabled: q.trim().length > 0,
    placeholderData: keepPreviousData,
  });
}
export function usePost(id: string, initialData?: Post) {
  return useQuery({ queryKey: qk.post(id), queryFn: () => getPost(id), initialData });
}
export function useComments(postId: string, initialData?: Comment[]) {
  return useQuery({ queryKey: qk.comments(postId), queryFn: () => getComments(postId), initialData });
}
/** 단일 상품(스토어 상세). 인자 있는 fetcher → 화살표로 감싼다. */
export function useProduct(id: string, initialData?: Product) {
  return useQuery({ queryKey: qk.product(id), queryFn: () => getProduct(id), initialData });
}
/** 주문 목록 — mock. 서버 initialData 하이드레이션. */
export function useOrders(initialData?: Order[]) {
  return useQuery({ queryKey: qk.orders, queryFn: getOrders, initialData });
}
/** 단일 주문 — mock. */
export function useOrder(id: string, initialData?: Order) {
  return useQuery({ queryKey: qk.order(id), queryFn: () => getOrder(id), initialData });
}
/** 알림 목록 — mock. */
export function useNotifications(initialData?: Notification[]) {
  return useQuery({ queryKey: qk.notifications, queryFn: getNotifications, initialData });
}
/** 구독 목록 — mock. */
export function useSubscriptions(initialData?: Subscription[]) {
  return useQuery({ queryKey: qk.subscriptions, queryFn: getSubscriptions, initialData });
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
 * 좋아요 토글 — 낙관적. 포스트 상세(qk.post)·피드(qk.feed)·포스트 목록(["posts", …],
 * 프로필/크리에이터 포함) 캐시를 동시 갱신 후 실패 시 전부 롤백. ※목업: 실 API 미연동.
 * apply는 멱등: 이미 같은 상태면 무변경(중복 클릭·재적용 방어), likeCount는 0 미만 클램프.
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
      await qc.cancelQueries({ queryKey: ["posts"] });
      const prevPost = qc.getQueryData<Post>(qk.post(id));
      const prevFeed = qc.getQueryData<Post[]>(qk.feed);
      const prevLists = qc.getQueriesData<Post[]>({ queryKey: ["posts"] });
      const apply = (p: Post): Post => {
        // 멱등: 대상이 아니거나 이미 같은 liked 상태면 그대로. count는 0 미만 방지.
        if (p.id !== id || p.liked === next) return p;
        return { ...p, liked: next, likeCount: Math.max(0, p.likeCount + (next ? 1 : -1)) };
      };
      qc.setQueryData<Post | undefined>(qk.post(id), (p) => (p ? apply(p) : p));
      qc.setQueryData<Post[] | undefined>(qk.feed, (list) => list?.map(apply));
      qc.setQueriesData<Post[]>({ queryKey: ["posts"] }, (list) => list?.map(apply));
      return { prevPost, prevFeed, prevLists, id };
    },
    onError: (_e, _v, ctx) => {
      if (!ctx) return;
      if (ctx.prevPost) qc.setQueryData(qk.post(ctx.id), ctx.prevPost);
      if (ctx.prevFeed) qc.setQueryData(qk.feed, ctx.prevFeed);
      ctx.prevLists?.forEach(([key, data]) => qc.setQueryData(key, data));
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
      await qc.cancelQueries({ queryKey: qk.post(postId) });
      const prev = qc.getQueryData<Comment[]>(qk.comments(postId));
      const prevPost = qc.getQueryData<Post>(qk.post(postId));
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
      return { prev, prevPost };
    },
    onError: (_e, _v, ctx) => {
      // 댓글 목록·포스트 commentCount 둘 다 낙관 갱신 → 롤백도 대칭으로 복원.
      if (ctx?.prev) qc.setQueryData(qk.comments(postId), ctx.prev);
      if (ctx?.prevPost) qc.setQueryData(qk.post(postId), ctx.prevPost);
    },
  });
}
