"use client";
import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { config } from "@/lib/config";
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
  apiToggleFollow,
  apiToggleLike,
  apiAddComment,
  apiCreateOrder,
  apiCancelOrder,
  apiRequestRefund,
  apiSubscribe,
  apiCancelSubscription,
  apiMarkNotificationRead,
  apiMarkAllNotificationsRead,
  apiReport,
  apiPublishPost,
} from "./index";
import type { Creator, Post, Comment, Product, Order, Notification, Subscription } from "./types";

/** 라이브 백엔드 연동 여부 — false면 뮤테이션은 낙관 로직만(sleep) 유지(오프라인·테스트). */
const USE_API = Boolean(config.apiUrl);

/** 네트워크 지연 시뮬레이션(목업 경로 전용). */
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
/** 주문 목록 — USE_API면 실 조회. 서버 initialData 하이드레이션. */
export function useOrders(initialData?: Order[]) {
  return useQuery({ queryKey: qk.orders, queryFn: getOrders, initialData });
}
/** 단일 주문 — USE_API면 실 조회. */
export function useOrder(id: string, initialData?: Order) {
  return useQuery({ queryKey: qk.order(id), queryFn: () => getOrder(id), initialData });
}
/** 알림 목록 — USE_API면 실 조회. */
export function useNotifications(initialData?: Notification[]) {
  return useQuery({ queryKey: qk.notifications, queryFn: getNotifications, initialData });
}
/** 구독 목록 — USE_API면 실 조회. */
export function useSubscriptions(initialData?: Subscription[]) {
  return useQuery({ queryKey: qk.subscriptions, queryFn: getSubscriptions, initialData });
}

/**
 * 팔로우 토글 — 낙관적. USE_API면 PUT/DELETE follow 실 호출 후 서버 카운트로 정정,
 * 아니면 mock(sleep). 실패 시 롤백.
 */
export function useToggleFollow(handle: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (next: boolean) => {
      if (USE_API) return apiToggleFollow(handle, next);
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
    onSuccess: (result) => {
      // 서버 응답의 실 카운트/상태로 정정(팔로워 수는 서버 권위).
      if (USE_API && typeof result === "object") {
        qc.setQueryData<Creator | undefined>(qk.creator(handle), (c) =>
          c ? { ...c, following: result.following, followers: result.followers } : c,
        );
      }
    },
    onSettled: () => {
      if (USE_API) {
        qc.invalidateQueries({ queryKey: qk.creator(handle) });
        // 디스커버리/추천 목록(qk.creators)의 following·팔로워 수 스테일 방지.
        qc.invalidateQueries({ queryKey: qk.creators });
      }
    },
  });
}

/**
 * 좋아요 토글 — 낙관적. 포스트 상세(qk.post)·피드(qk.feed)·포스트 목록(["posts", …])
 * 캐시를 동시 갱신 후 실패 시 전부 롤백. USE_API면 서버 카운트로 정정.
 * apply는 멱등: 이미 같은 상태면 무변경, likeCount는 0 미만 클램프.
 */
export function useToggleLike() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { id: string; next: boolean }) => {
      if (USE_API) return { ...v, result: await apiToggleLike(v.id, v.next) };
      await sleep(150);
      return { ...v };
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
    onSuccess: (data) => {
      if (!USE_API || !("result" in data) || !data.result) return;
      const { id, result } = data;
      const fix = (p: Post): Post =>
        p.id === id ? { ...p, liked: result.liked, likeCount: result.like_count } : p;
      qc.setQueryData<Post | undefined>(qk.post(id), (p) => (p ? fix(p) : p));
      qc.setQueryData<Post[] | undefined>(qk.feed, (list) => list?.map(fix));
      qc.setQueriesData<Post[]>({ queryKey: ["posts"] }, (list) => list?.map(fix));
    },
    onSettled: (data) => {
      if (USE_API && data) qc.invalidateQueries({ queryKey: qk.post(data.id) });
    },
  });
}

/**
 * 댓글 작성 — 낙관적. 댓글 목록(qk.comments)에 즉시 추가 + 포스트 commentCount 증가.
 * USE_API면 성공 시 임시 댓글을 서버 실 댓글로 치환. 실패 시 롤백.
 */
export function useAddComment(postId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: string) => {
      if (USE_API) return apiAddComment(postId, body);
      await sleep(150);
      return body;
    },
    onMutate: async (body: string) => {
      await qc.cancelQueries({ queryKey: qk.comments(postId) });
      await qc.cancelQueries({ queryKey: qk.post(postId) });
      const prev = qc.getQueryData<Comment[]>(qk.comments(postId));
      const prevPost = qc.getQueryData<Post>(qk.post(postId));
      const tmpId = `tmp-${prev?.length ?? 0}`;
      const optimistic: Comment = {
        id: tmpId,
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
      return { prev, prevPost, tmpId };
    },
    onError: (_e, _v, ctx) => {
      // 댓글 목록·포스트 commentCount 둘 다 낙관 갱신 → 롤백도 대칭으로 복원.
      if (ctx?.prev) qc.setQueryData(qk.comments(postId), ctx.prev);
      if (ctx?.prevPost) qc.setQueryData(qk.post(postId), ctx.prevPost);
    },
    onSuccess: (data, _body, ctx) => {
      // 임시 댓글(tmp-…)을 서버 실 댓글로 치환(id·작성자·시각 정정).
      if (USE_API && typeof data === "object" && ctx?.tmpId) {
        const real = data as Comment;
        qc.setQueryData<Comment[]>(qk.comments(postId), (list) =>
          list?.map((c) => (c.id === ctx.tmpId ? real : c)),
        );
      }
    },
    onSettled: () => {
      if (USE_API) qc.invalidateQueries({ queryKey: qk.comments(postId) });
    },
  });
}

/** 주문 생성(mock 결제 확정 — 실 PG 아님). 반환 Order(USE_API)/null(mock). */
export function useCreateOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { productId: string; qty: number; option?: string }) => {
      if (USE_API) return apiCreateOrder(input);
      await sleep(400);
      return null;
    },
    onSuccess: () => {
      if (USE_API) qc.invalidateQueries({ queryKey: qk.orders });
    },
  });
}

/** 주문 취소(paid/shipping) — 낙관적으로 status=cancelled. */
export function useCancelOrder(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (USE_API) return apiCancelOrder(id);
      await sleep(300);
      return null;
    },
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: qk.order(id) });
      const prev = qc.getQueryData<Order>(qk.order(id));
      qc.setQueryData<Order | undefined>(qk.order(id), (o) => (o ? { ...o, status: "cancelled" } : o));
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.order(id), ctx.prev);
    },
    onSuccess: (data) => {
      if (USE_API && data) qc.setQueryData(qk.order(id), data);
    },
    onSettled: () => {
      if (USE_API) {
        qc.invalidateQueries({ queryKey: qk.order(id) });
        qc.invalidateQueries({ queryKey: qk.orders });
      }
    },
  });
}

/** 환불 신청(shipping/completed) — 낙관적으로 refund 접수 표시. */
export function useRequestRefund(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { reason: string; detail?: string }) => {
      if (USE_API) return apiRequestRefund({ id, ...input });
      await sleep(300);
      return null;
    },
    onMutate: async (input: { reason: string; detail?: string }) => {
      await qc.cancelQueries({ queryKey: qk.order(id) });
      const prev = qc.getQueryData<Order>(qk.order(id));
      qc.setQueryData<Order | undefined>(qk.order(id), (o) =>
        o
          ? {
              ...o,
              // mock은 기존대로 refunding 전환, 실 API는 서버 상태(4종) 유지 후 성공 시 정정.
              status: USE_API ? o.status : "refunding",
              refund: { status: "requested", reason: input.reason, amount: o.total },
            }
          : o,
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.order(id), ctx.prev);
    },
    onSuccess: (data) => {
      if (USE_API && data) qc.setQueryData(qk.order(id), data);
    },
    onSettled: () => {
      if (USE_API) {
        qc.invalidateQueries({ queryKey: qk.order(id) });
        qc.invalidateQueries({ queryKey: qk.orders });
      }
    },
  });
}

/** 구독 시작(mock-paid). */
export function useSubscribe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { tierId: string }) => {
      if (USE_API) return apiSubscribe(input.tierId);
      await sleep(400);
      return null;
    },
    onSuccess: () => {
      if (USE_API) qc.invalidateQueries({ queryKey: qk.subscriptions });
    },
  });
}

/** 구독 해지(말일 해지) — 낙관적으로 cancelScheduled=true("해지 예정"). */
export function useCancelSubscription() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      if (USE_API) return apiCancelSubscription(id);
      await sleep(300);
      return id;
    },
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: qk.subscriptions });
      const prev = qc.getQueryData<Subscription[]>(qk.subscriptions);
      qc.setQueryData<Subscription[] | undefined>(qk.subscriptions, (list) =>
        list?.map((s) => (s.id === id ? { ...s, cancelScheduled: true } : s)),
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.subscriptions, ctx.prev);
    },
    onSuccess: (data) => {
      if (USE_API && typeof data !== "string") {
        qc.setQueryData<Subscription[] | undefined>(qk.subscriptions, (list) =>
          list?.map((s) => (s.id === data.id ? data : s)),
        );
      }
    },
    onSettled: () => {
      if (USE_API) qc.invalidateQueries({ queryKey: qk.subscriptions });
    },
  });
}

/** 알림 읽음 — 낙관적으로 read=true. */
export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      if (USE_API) return apiMarkNotificationRead(id);
      await sleep(120);
      return id;
    },
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: qk.notifications });
      const prev = qc.getQueryData<Notification[]>(qk.notifications);
      qc.setQueryData<Notification[] | undefined>(qk.notifications, (list) =>
        list?.map((n) => (n.id === id ? { ...n, read: true } : n)),
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.notifications, ctx.prev);
    },
    onSettled: () => {
      if (USE_API) qc.invalidateQueries({ queryKey: qk.notifications });
    },
  });
}

/** 알림 모두 읽음 — 낙관적으로 전체 read=true. */
export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (USE_API) return apiMarkAllNotificationsRead();
      await sleep(120);
      return null;
    },
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: qk.notifications });
      const prev = qc.getQueryData<Notification[]>(qk.notifications);
      qc.setQueryData<Notification[] | undefined>(qk.notifications, (list) =>
        list?.map((n) => ({ ...n, read: true })),
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.notifications, ctx.prev);
    },
    onSettled: () => {
      if (USE_API) qc.invalidateQueries({ queryKey: qk.notifications });
    },
  });
}

/** 콘텐츠 신고(팬 신고 — /safety/fan-reports). 접수만 하고 캐시 무관. */
export function useReport() {
  return useMutation({
    mutationFn: async (input: { reportType: string; narrative?: string }) => {
      if (USE_API) return apiReport(input);
      await sleep(200);
      return null;
    },
  });
}

/** 포스트 발행(크리에이터 오너만 — 403 시 호출측에서 안내). */
export function usePublishPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { body: string; mediaUrl?: string }) => {
      if (USE_API) return apiPublishPost(input);
      await sleep(300);
      return null;
    },
    onSuccess: () => {
      if (USE_API) {
        qc.invalidateQueries({ queryKey: qk.feed });
        qc.invalidateQueries({ queryKey: ["posts"] });
      }
    },
  });
}
