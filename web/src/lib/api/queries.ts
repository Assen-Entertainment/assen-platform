"use client";
import {
  useQuery,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
  type InfiniteData,
} from "@tanstack/react-query";
import {
  getCreatorsPage,
  getCreator,
  getProduct,
  getProductsPage,
  getMembershipTiers,
  getPostsPage,
  getStudioPostsPage,
  getPost,
  getCommentsPage,
  getFeedPage,
  getSearch,
  getCapabilities,
  getOrdersPage,
  getOrder,
  getNotificationsPage,
  getSubscriptions,
  getBlocks,
  getMarketingConsent,
  setMarketingConsent,
  mockSetBlocked,
  type Page,
  apiToggleFollow,
  apiBlockCreator,
  apiUnblockCreator,
  apiToggleLike,
  apiAddComment,
  apiCreateOrder,
  apiCreateOrderFree,
  apiCancelOrder,
  apiRequestRefund,
  apiSubscribe,
  apiSubscribeFree,
  apiCancelSubscription,
  apiChangeSubscriptionTier,
  apiMarkNotificationRead,
  apiMarkAllNotificationsRead,
  apiReport,
  apiPublishPost,
  apiUpdatePost,
  apiDeletePost,
  apiUpload,
  type PostUpdate,
  apiStartVerify,
  apiConfirmVerify,
  apiUpdateMe,
  getStudioStats,
  getStudioProducts,
  apiCreateStudioProduct,
  apiUpdateStudioProduct,
  apiDeleteStudioProduct,
  getStudioTiers,
  apiCreateStudioTier,
  apiUpdateStudioTier,
  apiDeleteStudioTier,
  apiUpdateStudioProfile,
  getPaymentMethods,
  apiAddPaymentMethod,
  apiSetPrimaryPaymentMethod,
  apiRemovePaymentMethod,
  type StudioProductCreate,
  type StudioProductUpdate,
  type StudioTierCreate,
  type StudioTierUpdate,
  type StudioProfileUpdate,
} from "./index";
import type { Creator, CreatorSort, Post, Comment, Product, Order, Notification, Subscription, SavedPaymentMethod, ShippingAddress, BlockedCreator, MarketingConsentState, StudioStats } from "./types";
import type { StudioProduct, StudioTier } from "@/lib/studio-mock";
import { emitNotificationRead, emitAllNotificationsRead } from "./notification-events";
import { track } from "@/lib/analytics";

/**
 * 라이브 백엔드 연동 여부 — false면 뮤테이션은 낙관 로직만(sleep) 유지(오프라인·테스트).
 * 빌드타임 상수(NEXT_PUBLIC_API_URL 인라인)라 mock 분기(mockSetBlocked 등)가 라이브 빌드에서 DCE된다.
 */
const USE_API = Boolean(process.env.NEXT_PUBLIC_API_URL);

/** 네트워크 지연 시뮬레이션(목업 경로 전용). */
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// --- 커서 페이지네이션(R4-W1) 유틸 --------------------------------------------
/**
 * 리스트 캐시 형태 — 테스트/레거시는 배열, 실사용(무한 쿼리)은 커서 페이지(InfiniteData).
 * 낙관적 뮤테이션이 양쪽을 모두 안전하게 갱신하도록 공용 헬퍼로 다룬다(회귀 0).
 */
type ListCache<T> = T[] | InfiniteData<Page<T>, string | undefined>;

/**
 * SSR Page 시드 → 무한 쿼리 initialData(첫 페이지). Page형(items+nextCursor)이라 nextCursor가
 * 처음부터 있어 hasNextPage가 마운트 즉시 정확 → initialDataUpdatedAt:0 없이도 이중 페치 없이
 * 더보기 노출(신선 60s 캐시 존중). mock 폴백은 단일 페이지(nextCursor 없음 → hasNextPage=false).
 */
function seedInfinite<T>(page?: Page<T>): InfiniteData<Page<T>, string | undefined> | undefined {
  return page ? { pages: [page], pageParams: [undefined] } : undefined;
}

/** 무한 페이지 → 평탄화 배열(뷰는 배열만 소비 — data 접근부 무변경). */
function flattenPages<T>(data: InfiniteData<Page<T>, string | undefined>): T[] {
  return data.pages.flatMap((pg) => pg.items);
}

/** 다음 페이지 커서(없으면 undefined → hasNextPage=false). */
function nextPageParam<T>(last: Page<T>): string | undefined {
  return last.nextCursor ?? undefined;
}

/** 리스트 캐시의 각 항목에 fn 적용(배열/InfiniteData 공용). */
function mapListCache<T>(data: ListCache<T> | undefined, fn: (item: T) => T): ListCache<T> | undefined {
  if (!data) return data;
  if (Array.isArray(data)) return data.map(fn);
  return { ...data, pages: data.pages.map((pg) => ({ ...pg, items: pg.items.map(fn) })) };
}

/** 리스트 캐시에서 keep=false 항목 제거(배열/InfiniteData 공용) — 차단 시 해당 크리에이터 포스트 제거. */
function filterListCache<T>(
  data: ListCache<T> | undefined,
  keep: (item: T) => boolean,
): ListCache<T> | undefined {
  if (!data) return data;
  if (Array.isArray(data)) return data.filter(keep);
  return { ...data, pages: data.pages.map((pg) => ({ ...pg, items: pg.items.filter(keep) })) };
}

/** 리스트 캐시 끝에 항목 추가(배열/InfiniteData 공용). 빈 캐시는 배열로 시드. */
function appendListCache<T>(data: ListCache<T> | undefined, item: T): ListCache<T> {
  if (!data) return [item];
  if (Array.isArray(data)) return [...data, item];
  const pages = data.pages.length ? data.pages : [{ items: [] as T[], nextCursor: undefined }];
  const lastIdx = pages.length - 1;
  return {
    ...data,
    pages: pages.map((pg, i) => (i === lastIdx ? { ...pg, items: [...pg.items, item] } : pg)),
  };
}

/** 리스트 캐시 항목 수(tmp id 생성용 — 배열/InfiniteData 공용). */
function countListCache<T>(data: ListCache<T> | undefined): number {
  if (!data) return 0;
  if (Array.isArray(data)) return data.length;
  return data.pages.reduce((n, pg) => n + pg.items.length, 0);
}

/** 리스트 캐시에 조건 만족 항목이 있는지(배열/InfiniteData 공용). 읽음 전 미읽음 여부 판정용. */
function someListCache<T>(data: ListCache<T> | undefined, pred: (item: T) => boolean): boolean {
  if (!data) return false;
  if (Array.isArray(data)) return data.some(pred);
  return data.pages.some((pg) => pg.items.some(pred));
}

/** 쿼리 키 */
export const qk = {
  creators: ["creators"] as const,
  creator: (handle: string) => ["creator", handle] as const,
  products: (creatorId?: string) => ["products", creatorId ?? "all"] as const,
  product: (id: string) => ["product", id] as const,
  tiers: (id?: string) => ["tiers", id ?? "all"] as const,
  posts: (id?: string) => ["posts", id ?? "all"] as const,
  // 스튜디오 오너 포스트 — 공용 ["posts"] 네임스페이스 하위 키. useUpdatePost/useDeletePost의
  // 낙관 갱신·무효화(["posts"] prefix)가 오너 목록에도 자동 반영되도록 같은 prefix를 공유한다.
  studioPosts: ["posts", "studio"] as const,
  feed: ["feed"] as const,
  post: (id: string) => ["post", id] as const,
  comments: (postId: string) => ["comments", postId] as const,
  search: (q: string) => ["search", q] as const,
  orders: ["orders"] as const,
  order: (id: string) => ["order", id] as const,
  notifications: ["notifications"] as const,
  subscriptions: ["subscriptions"] as const,
  blocks: ["blocks"] as const,
  marketing: ["marketing"] as const,
  capabilities: ["capabilities"] as const,
  paymentMethods: ["payment-methods"] as const,
  studioStats: ["studio-stats"] as const,
  studioProducts: ["studio-products"] as const,
  studioTiers: ["studio-tiers"] as const,
};

/**
 * 크리에이터 목록 — 커서 무한 쿼리(디스커버리). select로 평탄화해 소비처는 배열만 보고
 * (data 접근부 무변경), 더보기는 hasNextPage/fetchNextPage로 배선한다. mock=단일 페이지.
 * SSR Page 시드(nextCursor 포함)로 마운트 즉시 hasNextPage 정확 → 이중 페치 없이 더보기 노출.
 *
 * `sort`(E11 서버 랭킹 — popular/new/recommended) 지정 시 별도 쿼리 키(["creators", sort])로
 * 캐시가 분리되고, 서버가 이미 단일 랭킹 페이지(next_cursor 없음)를 반환하므로 hasNextPage=false로
 * 자연히 수렴한다(무한 쿼리 셸을 그대로 재사용 — 별도 훅 불필요). qk.creators 접두 무효화(팔로우
 * 토글 등)는 partial match로 sort 변형에도 그대로 적용된다.
 */
export function useCreators(initialData?: Page<Creator>, sort?: CreatorSort) {
  return useInfiniteQuery({
    queryKey: sort ? [...qk.creators, sort] : qk.creators,
    queryFn: ({ pageParam }) => getCreatorsPage(pageParam, sort),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextPageParam,
    initialData: seedInfinite(initialData),
    select: flattenPages,
  });
}
export function useCreator(handle: string, initialData?: Creator) {
  return useQuery({ queryKey: qk.creator(handle), queryFn: () => getCreator(handle), initialData });
}
/**
 * 상품 목록 — 커서 무한 쿼리(스토어·디스커버리). select로 평탄화해 뷰는 배열만 소비하고
 * (data 접근부 무변경), 더보기는 hasNextPage/fetchNextPage로 배선한다. mock=단일 페이지.
 */
export function useProducts(creatorId?: string, initialData?: Page<Product>) {
  return useInfiniteQuery({
    queryKey: qk.products(creatorId),
    queryFn: ({ pageParam }) => getProductsPage(creatorId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextPageParam,
    // SSR Page 시드(nextCursor 포함)로 마운트 즉시 hasNextPage 정확 → 이중 페치 없이 더보기 노출.
    initialData: seedInfinite(initialData),
    select: flattenPages,
  });
}
export function useMembershipTiers(id?: string) {
  return useQuery({ queryKey: qk.tiers(id), queryFn: () => getMembershipTiers(id) });
}
/** 크리에이터 포스트 — 커서 무한 쿼리. select 평탄화(뷰 무변경). mock=단일 페이지. */
export function usePosts(id?: string, initialData?: Page<Post>) {
  return useInfiniteQuery({
    queryKey: qk.posts(id),
    queryFn: ({ pageParam }) => getPostsPage(id, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextPageParam,
    // SSR Page 시드(nextCursor 포함)로 마운트 즉시 hasNextPage 정확 → 이중 페치 없이 더보기 노출.
    initialData: seedInfinite(initialData),
    select: flattenPages,
  });
}
/**
 * 스튜디오 오너 포스트 — GET /studio/posts(오너 스코프, 소비자 게이트 미적용) 커서 무한 쿼리.
 * 소비자용 usePosts(creatorId)의 fan_id 오용(라이브 빈 목록·오너 19+ 미표시) 대체 —
 * 오너가 자신의 전체 포스트(draft·19+ 포함)를 본다. 쿼리 키는 ["posts","studio"](공용 prefix)라
 * useUpdatePost/useDeletePost의 낙관 갱신·무효화가 자동 반영된다. mock=데모 오너 c1 목록.
 * 403(OwnerRequired, 비크리에이터)은 retry 없이 error로 노출 → 페이지가 방어 안내 렌더.
 */
export function useStudioPosts() {
  return useInfiniteQuery({
    queryKey: qk.studioPosts,
    queryFn: ({ pageParam }) => getStudioPostsPage(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextPageParam,
    select: flattenPages,
    retry: false,
  });
}
/**
 * 피드 — B2 `/feed` 커서 무한 쿼리(B3 개인화 배선 지점). 서버 Page initialData 하이드레이션으로
 * 마운트 즉시 nextCursor 확보 → 이중 페치 없이 더보기. mock=단일 페이지.
 */
export function useFeed(initialData?: Page<Post>) {
  return useInfiniteQuery({
    queryKey: qk.feed,
    queryFn: ({ pageParam }) => getFeedPage(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextPageParam,
    // SSR Page 시드(nextCursor 포함)로 마운트 즉시 hasNextPage 정확 → 이중 페치 없이 더보기 노출.
    initialData: seedInfinite(initialData),
    select: flattenPages,
  });
}
/**
 * 검색 — B2 `/search?q=&limit=&offset=` offset 무한 쿼리(더 보기). 빈 질의는 비활성, 타이핑 중
 * 직전 결과 유지. select로 누적 페이지를 creators/products로 평탄화(소비처는 배열만 본다) —
 * hasNextPage/fetchNextPage는 훅 반환값에서 그대로 노출되어 검색 뷰의 "더 보기" 버튼을 배선한다.
 */
export function useSearch(q: string) {
  return useInfiniteQuery({
    queryKey: qk.search(q),
    queryFn: ({ pageParam }) => getSearch(q, { offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (last) => last.nextOffset ?? undefined,
    enabled: q.trim().length > 0,
    placeholderData: keepPreviousData,
    select: (data) => ({
      creators: data.pages.flatMap((p) => p.creators),
      products: data.pages.flatMap((p) => p.products),
    }),
  });
}
export function usePost(id: string, initialData?: Post) {
  return useQuery({ queryKey: qk.post(id), queryFn: () => getPost(id), initialData });
}
/** 댓글 — 커서 무한 쿼리(포스트 상세). select 평탄화(뷰 무변경). mock=단일 페이지. */
export function useComments(postId: string, initialData?: Page<Comment>) {
  return useInfiniteQuery({
    queryKey: qk.comments(postId),
    queryFn: ({ pageParam }) => getCommentsPage(postId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextPageParam,
    // SSR Page 시드(nextCursor 포함)로 마운트 즉시 hasNextPage 정확 → 이중 페치 없이 더보기 노출.
    initialData: seedInfinite(initialData),
    select: flattenPages,
  });
}
/** 단일 상품(스토어 상세). 인자 있는 fetcher → 화살표로 감싼다. */
export function useProduct(id: string, initialData?: Product) {
  return useQuery({ queryKey: qk.product(id), queryFn: () => getProduct(id), initialData });
}
/** 주문 목록 — 커서 무한 쿼리. select 평탄화. 서버 initialData 하이드레이션. mock=단일 페이지. */
export function useOrders(initialData?: Page<Order>) {
  return useInfiniteQuery({
    queryKey: qk.orders,
    queryFn: ({ pageParam }) => getOrdersPage(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextPageParam,
    // SSR Page 시드(nextCursor 포함)로 마운트 즉시 hasNextPage 정확 → 이중 페치 없이 더보기 노출.
    initialData: seedInfinite(initialData),
    select: flattenPages,
  });
}
/** 단일 주문 — USE_API면 실 조회. */
export function useOrder(id: string, initialData?: Order) {
  return useQuery({ queryKey: qk.order(id), queryFn: () => getOrder(id), initialData });
}
/** 알림 목록 — 커서 무한 쿼리. select 평탄화. 서버 initialData 하이드레이션. mock=단일 페이지. */
export function useNotifications(initialData?: Page<Notification>) {
  return useInfiniteQuery({
    queryKey: qk.notifications,
    queryFn: ({ pageParam }) => getNotificationsPage(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextPageParam,
    // SSR Page 시드(nextCursor 포함)로 마운트 즉시 hasNextPage 정확 → 이중 페치 없이 더보기 노출.
    initialData: seedInfinite(initialData),
    select: flattenPages,
  });
}
/** 구독 목록 — USE_API면 실 조회. */
export function useSubscriptions(initialData?: Subscription[]) {
  return useQuery({ queryKey: qk.subscriptions, queryFn: getSubscriptions, initialData });
}

/**
 * 런타임 capability 플래그(ASS-287) — GET /api/capabilities(서버 설정 단일 출처). 배송 결제 게이트
 * UI가 소비한다. 자주 바뀌지 않으므로 staleTime을 길게 잡아 과도한 재요청을 막는다. mock 폴백은
 * getCapabilities가 게이트 닫힘(shipping=false)을 반환한다(fail-closed).
 */
export function useCapabilities() {
  return useQuery({ queryKey: qk.capabilities, queryFn: getCapabilities, staleTime: 5 * 60_000 });
}

/**
 * 배송(굿즈) 결제 가용 여부 — 로딩/오류/mock 중이면 false(fail-closed). 굿즈 CTA·배송지 PII 폼을
 * 서버 게이트가 열려 있다고 확인되기 전까지 노출하지 않기 위한 단일 판정점(방어심층).
 */
export function useShippingCheckoutAvailable(): boolean {
  const { data } = useCapabilities();
  return data?.shippingCheckoutAvailable === true;
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
      // 낙관적: following 뿐 아니라 팔로워 수도 ±1 즉시 반영해 "살아있는 숫자"(틱업)를 만든다.
      // 실 경로는 onSuccess에서 서버 권위 카운트로 정정하고, mock에서는 이 낙관적 값이 그대로 유지된다.
      qc.setQueryData<Creator | undefined>(qk.creator(handle), (c) =>
        c ? { ...c, following: next, followers: Math.max(0, c.followers + (next ? 1 : -1)) } : c,
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.creator(handle), ctx.prev);
    },
    onSuccess: (result) => {
      // 계측(단일 발화) — mock=boolean, 실 경로=FollowResult. following 상태만(PII 없음).
      track("follow_toggled", { following: typeof result === "object" ? result.following : result });
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
      const prevFeed = qc.getQueryData<ListCache<Post>>(qk.feed);
      const prevLists = qc.getQueriesData<ListCache<Post>>({ queryKey: ["posts"] });
      const apply = (p: Post): Post => {
        // 멱등: 대상이 아니거나 이미 같은 liked 상태면 그대로. count는 0 미만 방지.
        if (p.id !== id || p.liked === next) return p;
        return { ...p, liked: next, likeCount: Math.max(0, p.likeCount + (next ? 1 : -1)) };
      };
      // post(id)는 단건, feed·["posts"]는 리스트 캐시(배열/무한 페이지 공용) — 대칭 갱신.
      qc.setQueryData<Post | undefined>(qk.post(id), (p) => (p ? apply(p) : p));
      qc.setQueryData<ListCache<Post>>(qk.feed, (d) => mapListCache(d, apply));
      qc.setQueriesData<ListCache<Post>>({ queryKey: ["posts"] }, (d) => mapListCache(d, apply));
      return { prevPost, prevFeed, prevLists, id };
    },
    onError: (_e, _v, ctx) => {
      if (!ctx) return;
      if (ctx.prevPost) qc.setQueryData(qk.post(ctx.id), ctx.prevPost);
      if (ctx.prevFeed) qc.setQueryData(qk.feed, ctx.prevFeed);
      ctx.prevLists?.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSuccess: (data) => {
      // 계측(단일 발화) — 좋아요 토글 상태(liked)만. mock/실 경로 공통 data.next.
      track("post_liked", { liked: data.next });
      if (!USE_API || !("result" in data) || !data.result) return;
      const { id, result } = data;
      const fix = (p: Post): Post =>
        p.id === id ? { ...p, liked: result.liked, likeCount: result.like_count } : p;
      qc.setQueryData<Post | undefined>(qk.post(id), (p) => (p ? fix(p) : p));
      qc.setQueryData<ListCache<Post>>(qk.feed, (d) => mapListCache(d, fix));
      qc.setQueriesData<ListCache<Post>>({ queryKey: ["posts"] }, (d) => mapListCache(d, fix));
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
      const prev = qc.getQueryData<ListCache<Comment>>(qk.comments(postId));
      const prevPost = qc.getQueryData<Post>(qk.post(postId));
      const tmpId = `tmp-${countListCache(prev)}`;
      const optimistic: Comment = {
        id: tmpId,
        postId,
        author: "나",
        authorFallback: "나",
        body,
        createdAt: "방금",
      };
      qc.setQueryData<ListCache<Comment>>(qk.comments(postId), (d) => appendListCache(d, optimistic));
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
      // 계측(단일 발화) — 대상 포스트 id만(댓글 본문은 담지 않는다·PII 차단).
      track("comment_created", { postId });
      // 임시 댓글(tmp-…)을 서버 실 댓글로 치환(id·작성자·시각 정정).
      if (USE_API && typeof data === "object" && ctx?.tmpId) {
        const real = data as Comment;
        qc.setQueryData<ListCache<Comment>>(qk.comments(postId), (d) =>
          mapListCache(d, (c) => (c.id === ctx.tmpId ? real : c)),
        );
      }
    },
    onSettled: () => {
      if (USE_API) qc.invalidateQueries({ queryKey: qk.comments(postId) });
    },
  });
}

/** 주문 생성(mock 결제 확정 — 실 PG 아님). 배송 상품이면 shipping(배송지) 동봉. 반환 Order(USE_API)/null(mock). */
export function useCreateOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      productId: string;
      qty: number;
      option?: string;
      shipping?: ShippingAddress;
      idempotencyKey?: string;
    }) => {
      if (USE_API) return apiCreateOrder(input);
      await sleep(400);
      return null;
    },
    onSuccess: (_data, variables) => {
      // 계측(단일 발화) — 상품 id·수량만. 배송지 등 PII는 담지 않는다.
      track("order_created", { productId: variables.productId, qty: variables.qty });
      if (USE_API) qc.invalidateQueries({ queryKey: qk.orders });
    },
  });
}

/**
 * 무료 상품 획득(ASS-297) — 결제 없이 apiCreateOrderFree(/orders/free)로 획득. 배송(굿즈)은
 * 유료 경로와 동일하게 동봉한다(무료는 결제만 뺀다). useCreateOrder와 동일한 무효화(qk.orders).
 */
export function useCreateOrderFree() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { productId: string; qty: number; option?: string; shipping?: ShippingAddress }) => {
      if (USE_API) return apiCreateOrderFree(input);
      await sleep(400);
      return null;
    },
    onSuccess: (_data, variables) => {
      track("order_created", { productId: variables.productId, qty: variables.qty });
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
    onSuccess: (_data, variables) => {
      track("subscription_started", { tierId: variables.tierId });
      if (USE_API) qc.invalidateQueries({ queryKey: qk.subscriptions });
    },
  });
}

/**
 * 무료 멤버십 가입(ASS-297) — 결제 없이 apiSubscribeFree(/subscriptions/free)로 가입.
 * useSubscribe와 동일한 무효화(qk.subscriptions). 무료 멤버십은 결제 앵커/자동전환이 없다.
 */
export function useSubscribeFree() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { tierId: string }) => {
      if (USE_API) return apiSubscribeFree(input.tierId);
      await sleep(400);
      return null;
    },
    onSuccess: (_data, variables) => {
      track("subscription_started", { tierId: variables.tierId });
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

/**
 * 구독 티어 전환(업/다운그레이드) — 낙관적으로 해당 구독의 tierId 즉시 반영("구독 중" 배지 이동),
 * 성공 시 서버 SubscriptionOut(가격·티어명 정정)로 교체. 실패 시 롤백.
 * 티어 목록(qk.tiers)도 무효화 — 프로필 멤버십 탭이 최신 상태를 반영하도록.
 */
export function useChangeSubscriptionTier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { id: string; tierId: string }) => {
      if (USE_API) return apiChangeSubscriptionTier(input.id, input.tierId);
      await sleep(300);
      return input;
    },
    onMutate: async ({ id, tierId }: { id: string; tierId: string }) => {
      await qc.cancelQueries({ queryKey: qk.subscriptions });
      const prev = qc.getQueryData<Subscription[]>(qk.subscriptions);
      qc.setQueryData<Subscription[] | undefined>(qk.subscriptions, (list) =>
        list?.map((s) => (s.id === id ? { ...s, tierId } : s)),
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.subscriptions, ctx.prev);
    },
    onSuccess: (data, variables) => {
      track("tier_changed", { tierId: variables.tierId });
      // 실 경로: 서버 Subscription(가격·티어명 반영)으로 해당 구독 전체 교체. mock({id,tierId})은 낙관값 유지.
      if (USE_API && typeof data === "object" && "tierName" in data) {
        const sub = data as Subscription;
        qc.setQueryData<Subscription[] | undefined>(qk.subscriptions, (list) =>
          list?.map((s) => (s.id === sub.id ? sub : s)),
        );
      }
    },
    onSettled: () => {
      if (USE_API) {
        qc.invalidateQueries({ queryKey: qk.subscriptions });
        qc.invalidateQueries({ queryKey: ["tiers"] });
      }
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
      const prev = qc.getQueryData<ListCache<Notification>>(qk.notifications);
      // 캐시에서 이미 읽음으로 확인되는 경우만 감소 생략(중복 감소 방지) — 그 외엔 미읽음으로 간주.
      const wasUnread = !someListCache(prev, (n) => n.id === id && n.read === true);
      qc.setQueryData<ListCache<Notification>>(qk.notifications, (d) =>
        mapListCache(d, (n) => (n.id === id ? { ...n, read: true } : n)),
      );
      return { prev, wasUnread };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.notifications, ctx.prev);
    },
    onSuccess: (_data, _id, ctx) => {
      // 실시간 뱃지(useNotificationSocket) 스테일-하이 해소 — 읽은 만큼 소켓 카운트 감소.
      if (ctx?.wasUnread) emitNotificationRead();
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
      const prev = qc.getQueryData<ListCache<Notification>>(qk.notifications);
      qc.setQueryData<ListCache<Notification>>(qk.notifications, (d) =>
        mapListCache(d, (n) => ({ ...n, read: true })),
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.notifications, ctx.prev);
    },
    onSuccess: () => {
      // 서버 read-all은 전체를 읽음 처리 → 실시간 뱃지도 0으로 재동기(스테일-하이 해소).
      emitAllNotificationsRead();
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
    onSuccess: (_data, variables) => {
      // 계측(단일 발화) — 신고 유형 코드만. 서술(narrative)은 담지 않는다(PII·자유 텍스트 차단).
      track("report_submitted", { reportType: variables.reportType });
    },
  });
}

// --- 안전(R4-W3): 팬 개인 차단(CreatorBlock) --------------------------------
/** 내 차단 목록(설정 차단 화면). */
export function useBlocks() {
  return useQuery({ queryKey: qk.blocks, queryFn: getBlocks });
}

// --- 마케팅 수신 동의(D8) — 채널별 opt-in 설정 --------------------------------
/** 내 마케팅 수신 동의(설정 화면). 비로그인/오프라인은 전부 off(fail-closed). */
export function useMarketingConsent() {
  return useQuery({ queryKey: qk.marketing, queryFn: getMarketingConsent });
}

/** 마케팅 수신 동의 저장(채널 전체 상태) — 성공 시 캐시를 서버 응답으로 갱신. */
export function useSetMarketingConsent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (state: MarketingConsentState) => setMarketingConsent(state),
    onSuccess: (data) => {
      qc.setQueryData(qk.marketing, data);
    },
  });
}

/**
 * 크리에이터 차단 — 낙관적. 프로필(핸들 알 때) blocked=true + 자동 언팔로우(following=false),
 * 피드·포스트 목록에서 해당 크리에이터 포스트 즉시 제거(차단이 피드/디스커버리/검색/팔로우에 영향).
 * USE_API면 서버 상태로 정정 후 관련 쿼리(feed·creators·search·posts·해당 creator·blocks) 무효화 —
 * 자동 언팔 반영. mock은 로컬 상태(mockSetBlocked)로 설정 목록 코히어런스 유지. 실패 시 롤백.
 */
export function useBlockCreator() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { creatorId: string; handle?: string }) => {
      if (USE_API) return apiBlockCreator(input.creatorId);
      await sleep(200);
      mockSetBlocked(input.creatorId, true);
      return null;
    },
    onMutate: async ({ creatorId, handle }: { creatorId: string; handle?: string }) => {
      // 프로필 크리에이터 캐시(핸들 알 때): blocked=true + 자동 언팔로우.
      let prevCreator: Creator | undefined;
      if (handle) {
        await qc.cancelQueries({ queryKey: qk.creator(handle) });
        prevCreator = qc.getQueryData<Creator>(qk.creator(handle));
        qc.setQueryData<Creator | undefined>(qk.creator(handle), (c) =>
          c ? { ...c, blocked: true, following: false } : c,
        );
      }
      // 피드·포스트 목록에서 차단 크리에이터 포스트 제거(즉시 사라짐).
      await qc.cancelQueries({ queryKey: qk.feed });
      await qc.cancelQueries({ queryKey: ["posts"] });
      const prevFeed = qc.getQueryData<ListCache<Post>>(qk.feed);
      const prevLists = qc.getQueriesData<ListCache<Post>>({ queryKey: ["posts"] });
      const keep = (p: Post) => p.creatorId !== creatorId;
      qc.setQueryData<ListCache<Post>>(qk.feed, (d) => filterListCache(d, keep));
      qc.setQueriesData<ListCache<Post>>({ queryKey: ["posts"] }, (d) => filterListCache(d, keep));
      return { prevCreator, prevFeed, prevLists, handle };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.handle && ctx.prevCreator) qc.setQueryData(qk.creator(ctx.handle), ctx.prevCreator);
      if (ctx?.prevFeed) qc.setQueryData(qk.feed, ctx.prevFeed);
      ctx?.prevLists?.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSuccess: (result, { handle }) => {
      track("block_toggled", { blocked: true });
      // 서버 응답(BlockResult)으로 정정 — blocked 반영 + 자동 언팔 유지.
      if (USE_API && result && handle) {
        qc.setQueryData<Creator | undefined>(qk.creator(handle), (c) =>
          c ? { ...c, blocked: result.blocked, following: false } : c,
        );
      }
    },
    onSettled: (_d, _e, { handle }) => {
      if (USE_API) {
        qc.invalidateQueries({ queryKey: qk.feed });
        qc.invalidateQueries({ queryKey: qk.creators });
        qc.invalidateQueries({ queryKey: ["posts"] });
        qc.invalidateQueries({ queryKey: ["search"] });
        qc.invalidateQueries({ queryKey: qk.blocks });
        if (handle) qc.invalidateQueries({ queryKey: qk.creator(handle) });
      }
    },
  });
}

/**
 * 크리에이터 차단 해제 — 낙관적. 프로필 blocked=false(자동 재팔로우 없음), 설정 차단 목록에서 즉시 제거.
 * USE_API면 관련 쿼리 무효화. mock은 mockSetBlocked(false)로 설정 목록 코히어런스 유지. 실패 시 롤백.
 */
export function useUnblockCreator() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { creatorId: string; handle?: string }) => {
      if (USE_API) return apiUnblockCreator(input.creatorId);
      await sleep(200);
      mockSetBlocked(input.creatorId, false);
      return null;
    },
    onMutate: async ({ creatorId, handle }: { creatorId: string; handle?: string }) => {
      let prevCreator: Creator | undefined;
      if (handle) {
        await qc.cancelQueries({ queryKey: qk.creator(handle) });
        prevCreator = qc.getQueryData<Creator>(qk.creator(handle));
        qc.setQueryData<Creator | undefined>(qk.creator(handle), (c) => (c ? { ...c, blocked: false } : c));
      }
      // 설정 차단 목록에서 즉시 제거.
      await qc.cancelQueries({ queryKey: qk.blocks });
      const prevBlocks = qc.getQueryData<BlockedCreator[]>(qk.blocks);
      qc.setQueryData<BlockedCreator[] | undefined>(qk.blocks, (list) =>
        list?.filter((b) => b.creatorId !== creatorId),
      );
      return { prevCreator, prevBlocks, handle };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.handle && ctx.prevCreator) qc.setQueryData(qk.creator(ctx.handle), ctx.prevCreator);
      if (ctx?.prevBlocks) qc.setQueryData(qk.blocks, ctx.prevBlocks);
    },
    onSuccess: () => {
      track("block_toggled", { blocked: false });
    },
    onSettled: (_d, _e, { handle }) => {
      if (USE_API) {
        qc.invalidateQueries({ queryKey: qk.feed });
        qc.invalidateQueries({ queryKey: qk.creators });
        qc.invalidateQueries({ queryKey: ["posts"] });
        qc.invalidateQueries({ queryKey: ["search"] });
        qc.invalidateQueries({ queryKey: qk.blocks });
        if (handle) qc.invalidateQueries({ queryKey: qk.creator(handle) });
      }
    },
  });
}

/**
 * 이미지 업로드(R12) — 선택 파일을 apiUpload로 올리고 반환 URL을 media_url로 쓴다(포스트·상품·아바타 공용).
 * 캐시 무관(단발 리소스 생성)이므로 mutationFn만 위임 — isPending으로 진행 상태, onError로 실패 토스트를 배선한다.
 * mock 폴백(USE_API=false)은 apiUpload 내부에서 objectURL을 반환한다(실 업로드 없음·번들 격리).
 */
export function useUploadImage() {
  return useMutation({ mutationFn: (file: File) => apiUpload(file) });
}

/** 포스트 발행(크리에이터 오너만 — 403 시 호출측에서 안내). isAdult=19+ 성인 등급(서버가 노출 통제). */
export function usePublishPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      body: string;
      mediaUrl?: string;
      isAdult?: boolean;
      visibility?: "public" | "members";
      requiredTier?: string | null;
    }) => {
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

/**
 * 포스트 수정(오너 — PATCH /posts/{id}). 성공 시 포스트 목록(["posts", …])·피드·상세 캐시의
 * 해당 항목을 갱신. 실 경로는 서버 Post로 전체 교체, mock은 제공 필드만 병합. 비오너/미지 id는 404.
 */
export function useUpdatePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { id: string } & PostUpdate) => {
      const { id, ...patch } = input;
      if (USE_API) return apiUpdatePost(id, patch);
      await sleep(250);
      return { id, patch };
    },
    onSuccess: (result) => {
      // mock은 { id, patch }(patch 키로 판별) → 제공 필드만 병합. 실 경로는 Post 전체 교체.
      const apply = (p: Post): Post => {
        if ("patch" in result) {
          if (p.id !== result.id) return p;
          const { patch } = result;
          return {
            ...p,
            ...(patch.body !== undefined ? { body: patch.body } : {}),
            ...(patch.mediaUrl !== undefined ? { mediaUrl: patch.mediaUrl } : {}),
            ...(patch.isAdult !== undefined ? { isAdult: patch.isAdult } : {}),
          };
        }
        return p.id === result.id ? result : p;
      };
      qc.setQueriesData<ListCache<Post>>({ queryKey: ["posts"] }, (d) => mapListCache(d, apply));
      qc.setQueryData<ListCache<Post>>(qk.feed, (d) => mapListCache(d, apply));
      qc.setQueryData<Post | undefined>(qk.post(result.id), (p) => (p ? apply(p) : p));
      if (USE_API) {
        qc.invalidateQueries({ queryKey: ["posts"] });
        qc.invalidateQueries({ queryKey: qk.feed });
      }
    },
  });
}

/**
 * 포스트 삭제(오너 — DELETE /posts/{id}) — 낙관적으로 포스트 목록·피드에서 즉시 제거 후 실패 시 롤백.
 * 비오너/미지 id는 서버 404(no-leak). USE_API면 성공 시 관련 목록 무효화.
 */
export function useDeletePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      if (USE_API) await apiDeletePost(id);
      else await sleep(200);
      return id;
    },
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: ["posts"] });
      await qc.cancelQueries({ queryKey: qk.feed });
      const prevLists = qc.getQueriesData<ListCache<Post>>({ queryKey: ["posts"] });
      const prevFeed = qc.getQueryData<ListCache<Post>>(qk.feed);
      const keep = (p: Post) => p.id !== id;
      qc.setQueriesData<ListCache<Post>>({ queryKey: ["posts"] }, (d) => filterListCache(d, keep));
      qc.setQueryData<ListCache<Post>>(qk.feed, (d) => filterListCache(d, keep));
      return { prevLists, prevFeed };
    },
    onError: (_e, _v, ctx) => {
      ctx?.prevLists?.forEach(([key, data]) => qc.setQueryData(key, data));
      if (ctx?.prevFeed) qc.setQueryData(qk.feed, ctx.prevFeed);
    },
    onSettled: () => {
      if (USE_API) {
        qc.invalidateQueries({ queryKey: ["posts"] });
        qc.invalidateQueries({ queryKey: qk.feed });
      }
    },
  });
}

// --- 게이트 기능(R3): KYC 본인인증 -------------------------------------------
/** 본인인증 시작 — 실 경로는 verify/start(503=미가용). mock은 즉시 통과 합성. */
export function useStartVerify() {
  return useMutation({
    mutationFn: async () => {
      if (USE_API) return apiStartVerify();
      await sleep(150);
      return undefined;
    },
  });
}
/**
 * 본인인증 확인 — 파생 플래그(adultVerified/kycStatus)를 반환. 세션 반영은 호출측이
 * `markAdultVerified(result)`로 수행(mock=로컬 persist·api=['auth','me'] 갱신). 503은 호출측 안내.
 */
export function useConfirmVerify() {
  return useMutation({
    mutationFn: async (): Promise<{ adultVerified: boolean; kycStatus: string }> => {
      if (USE_API) return apiConfirmVerify();
      await sleep(200);
      // mock: 결정적 통과(성인 인증 완료로 합성 — 실 검증 아님).
      return { adultVerified: true, kycStatus: "verified" };
    },
  });
}

// --- 게이트 기능(R3): 계정 수정 ----------------------------------------------
/** 내 닉네임 수정 — 낙관적 반영 + 세션 무효화. mock은 sleep 후 토스트만(로컬 세션 무변경). */
export function useUpdateMe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (nickname: string) => {
      if (USE_API) await apiUpdateMe(nickname);
      else await sleep(200);
      return nickname;
    },
    onMutate: async (nickname: string) => {
      await qc.cancelQueries({ queryKey: ["auth", "me"] });
      const prev = qc.getQueryData(["auth", "me"]);
      qc.setQueryData(["auth", "me"], (u: unknown) =>
        u && typeof u === "object" ? { ...u, name: nickname } : u,
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx && "prev" in ctx) qc.setQueryData(["auth", "me"], ctx.prev);
    },
    onSettled: () => {
      if (USE_API) qc.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

/** 스튜디오 프로필 수정(크리에이터 오너). 성공 시 관련 크리에이터 캐시 무효화. */
export function useUpdateStudioProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: StudioProfileUpdate) => {
      if (USE_API) return apiUpdateStudioProfile(input);
      await sleep(200);
      return null;
    },
    onSuccess: (creator) => {
      if (USE_API && creator) {
        qc.setQueryData(qk.creator(creator.handle), creator);
        qc.invalidateQueries({ queryKey: qk.creators });
      }
    },
  });
}

// --- R4-W5: 스튜디오 대시보드 실 카운트 --------------------------------------
/** 스튜디오 대시보드 실 카운트 — data가 null이면 비크리에이터/비로그인(호출측 빈 상태 안내). */
export function useStudioStats(initialData?: StudioStats | null) {
  return useQuery({ queryKey: qk.studioStats, queryFn: getStudioStats, initialData });
}

// --- 게이트 기능(R3): 스튜디오 카탈로그 쓰기 ---------------------------------
/** 오너 상품 목록. */
export function useStudioProducts() {
  return useQuery({ queryKey: qk.studioProducts, queryFn: getStudioProducts });
}
/** 상품 생성 — 성공 시 목록 앞에 추가(mock은 로컬 합성 행). */
export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: StudioProductCreate) => {
      if (USE_API) return apiCreateStudioProduct(input);
      await sleep(300);
      // mock 합성 행 — 실제 저장 없이 로컬 목록에 추가(기존 데모 동작 보존).
      const row: StudioProduct = {
        id: `new-${Date.now()}`,
        type: input.type,
        title: input.title || "새 상품",
        price: input.price,
        status: input.status ?? "draft",
        // 방금 생성된 상품은 주문 이력이 없으므로 sold=0 (실 API 경로와 동일한 카운트 불변식).
        sold: 0,
        stock: null,
        updatedAt: "방금",
        pricingKind: input.pricingKind ?? "paid",
      };
      return row;
    },
    onSuccess: (created) => {
      qc.setQueryData<StudioProduct[]>(qk.studioProducts, (list) => [created, ...(list ?? [])]);
      if (USE_API) qc.invalidateQueries({ queryKey: qk.studioProducts });
    },
  });
}
/** 상품 수정 — 성공 시 해당 행 교체. */
export function useUpdateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { id: string } & StudioProductUpdate) => {
      const { id, ...patch } = input;
      if (USE_API) return apiUpdateStudioProduct(id, patch);
      await sleep(250);
      return { id, patch };
    },
    onSuccess: (result) => {
      qc.setQueryData<StudioProduct[]>(qk.studioProducts, (list) =>
        list?.map((p) => {
          // mock 낙관적 갱신은 { id, patch } 형태(patch 키로 판별) — 제공 필드만 병합(null stock=무제한 유지).
          if ("patch" in result) return p.id === result.id ? { ...p, ...result.patch } : p;
          return p.id === result.id ? result : p; // 실 경로: 전체 교체
        }),
      );
      if (USE_API) qc.invalidateQueries({ queryKey: qk.studioProducts });
    },
  });
}
/** 상품 삭제 — 성공 시 목록에서 제거. */
export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      if (USE_API) await apiDeleteStudioProduct(id);
      else await sleep(200);
      return id;
    },
    onSuccess: (id) => {
      qc.setQueryData<StudioProduct[]>(qk.studioProducts, (list) => list?.filter((p) => p.id !== id));
      if (USE_API) qc.invalidateQueries({ queryKey: qk.studioProducts });
    },
  });
}

/** 오너 티어 목록. */
export function useStudioTiers() {
  return useQuery({ queryKey: qk.studioTiers, queryFn: getStudioTiers });
}
/** 티어 생성 — 성공 시 목록에 추가. */
export function useCreateTier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: StudioTierCreate) => {
      if (USE_API) return apiCreateStudioTier(input);
      await sleep(300);
      const row: StudioTier = {
        id: `new-${Date.now()}`,
        name: input.name || "새 티어",
        price: input.price,
        benefits: input.benefits,
        // 방금 생성된 티어는 구독자가 없으므로 subscribers=0 (실 API 경로와 동일한 카운트 불변식).
        subscribers: 0,
        active: true,
        pricingKind: input.pricingKind ?? "paid",
      };
      return row;
    },
    onSuccess: (created) => {
      qc.setQueryData<StudioTier[]>(qk.studioTiers, (list) => [...(list ?? []), created]);
      if (USE_API) qc.invalidateQueries({ queryKey: qk.studioTiers });
    },
  });
}
/** 티어 수정 — 성공 시 해당 행 교체. */
export function useUpdateTier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { id: string } & StudioTierUpdate) => {
      const { id, ...patch } = input;
      if (USE_API) return apiUpdateStudioTier(id, patch);
      await sleep(250);
      return { id, patch };
    },
    onSuccess: (result) => {
      qc.setQueryData<StudioTier[]>(qk.studioTiers, (list) =>
        list?.map((t) => {
          // mock 낙관적 갱신은 { id, patch } 형태(patch 키로 판별).
          if ("patch" in result) return t.id === result.id ? { ...t, ...result.patch } : t; // mock: 병합
          return t.id === result.id ? result : t; // 실 경로: 전체 교체
        }),
      );
      if (USE_API) qc.invalidateQueries({ queryKey: qk.studioTiers });
    },
  });
}
/** 티어 삭제 — 성공 시 목록에서 제거. */
export function useDeleteTier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      if (USE_API) await apiDeleteStudioTier(id);
      else await sleep(200);
      return id;
    },
    onSuccess: (id) => {
      qc.setQueryData<StudioTier[]>(qk.studioTiers, (list) => list?.filter((t) => t.id !== id));
      if (USE_API) qc.invalidateQueries({ queryKey: qk.studioTiers });
    },
  });
}

// --- 게이트 기능(R3): 결제수단 ------------------------------------------------
/** 내 결제수단 목록. */
export function usePaymentMethods() {
  return useQuery({ queryKey: qk.paymentMethods, queryFn: getPaymentMethods });
}
/** 결제수단 등록 — brand + mock PG 토큰만 전송(raw PAN/CVC 미전송·PCI). 성공 시 목록에 추가. */
export function useAddPaymentMethod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { brand: string; makePrimary?: boolean }) => {
      if (USE_API) return apiAddPaymentMethod(input);
      await sleep(300);
      // mock 합성 — 실 카드정보 없이 표시용 더미(last4는 랜덤 4자리).
      const method: SavedPaymentMethod = {
        id: `m-${Date.now()}`,
        brand: input.brand || "새 카드",
        last4: String(1000 + Math.floor(Math.random() * 9000)),
        isPrimary: Boolean(input.makePrimary),
        createdAt: new Date().toISOString(),
      };
      return method;
    },
    onSuccess: (added) => {
      qc.setQueryData<SavedPaymentMethod[]>(qk.paymentMethods, (list) => {
        const base = added.isPrimary ? (list ?? []).map((m) => ({ ...m, isPrimary: false })) : list ?? [];
        return [...base, added];
      });
      if (USE_API) qc.invalidateQueries({ queryKey: qk.paymentMethods });
    },
  });
}
/** 기본 결제수단 지정 — 낙관적으로 단일 primary 보장. */
export function useSetPrimaryPaymentMethod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      if (USE_API) return apiSetPrimaryPaymentMethod(id);
      await sleep(200);
      return id;
    },
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: qk.paymentMethods });
      const prev = qc.getQueryData<SavedPaymentMethod[]>(qk.paymentMethods);
      qc.setQueryData<SavedPaymentMethod[]>(qk.paymentMethods, (list) =>
        list?.map((m) => ({ ...m, isPrimary: m.id === id })),
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.paymentMethods, ctx.prev);
    },
    onSettled: () => {
      if (USE_API) qc.invalidateQueries({ queryKey: qk.paymentMethods });
    },
  });
}
/** 결제수단 삭제 — 낙관적으로 제거. */
export function useRemovePaymentMethod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      if (USE_API) await apiRemovePaymentMethod(id);
      else await sleep(200);
      return id;
    },
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: qk.paymentMethods });
      const prev = qc.getQueryData<SavedPaymentMethod[]>(qk.paymentMethods);
      qc.setQueryData<SavedPaymentMethod[]>(qk.paymentMethods, (list) => list?.filter((m) => m.id !== id));
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.paymentMethods, ctx.prev);
    },
    onSettled: () => {
      if (USE_API) qc.invalidateQueries({ queryKey: qk.paymentMethods });
    },
  });
}
