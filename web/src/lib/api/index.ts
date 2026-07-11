/**
 * Assen 도메인 API — B2 백엔드 연동 (SDLC 09 B5).
 *
 * `config.apiUrl`(NEXT_PUBLIC_API_URL)가 설정되면 실 Django Ninja B2 API를 호출하고
 * snake_case→camelCase 매핑 + 커서 페이지 언랩을 수행한다. 미설정(빌드/CI/standalone)이면
 * 아래 mock으로 폴백 → `next build`(SSG)와 백엔드 없는 개발이 그대로 동작한다.
 * 계약 타입: openapi.json → schema.d.ts (openapi-typescript, `npm run gen:types`).
 */
import { apiFetch, ApiError } from "./client";
import type {
  BlockedCreator,
  Comment,
  Creator,
  CreatorSort,
  MembershipTier,
  Notification,
  NotificationKind,
  Order,
  OrderItem,
  OrderStatus,
  Paginated,
  Post,
  Product,
  RefundStatus,
  SavedPaymentMethod,
  ShippingAddress,
  StudioStats,
  Subscription,
  SearchResult,
} from "./types";
// 스튜디오 카탈로그 타입/목업은 studio-mock의 순수 유틸을 정본으로 재사용(데이터만 실 API로 전환).
import {
  STUDIO_PRODUCTS,
  STUDIO_TIERS,
  type StudioProduct,
  type StudioTier,
  type ProductStatus,
} from "@/lib/studio-mock";
// 스튜디오 재무 mock(정산/애널리틱스 placeholder 금액) — USE_API=false 폴백에서만 참조(ASS-289 #5
// 번들 격리). 라이브 빌드에선 아래 데드코드 분기가 접혀 이 모듈이 mock/data.ts와 동일하게
// 트리셰이킹된다 → 날조 금액이 라이브 산출물에서 제거된다.
import { SETTLEMENT_ROWS, ANALYTICS_SERIES, type SettlementRow, type AnalyticsPoint } from "@/lib/studio-mock-finance";
// mock 폴백 데이터/전용 로직 — USE_API=false 경로에서만 참조(R6-W2C 번들 격리).
// 라이브 빌드에선 USE_API가 빌드타임 상수 true로 접혀 아래 참조가 DCE → 이 모듈이 트리셰이킹된다.
import {
  CREATORS,
  PRODUCTS,
  TIERS,
  POSTS,
  COMMENTS,
  ORDERS,
  NOTIFICATIONS,
  SUBSCRIPTIONS,
  PAYMENT_METHODS,
  STUDIO_STATS,
  MOCK_BLOCKED,
} from "./mock/data";

export * from "./types";
export { apiFetch, ApiError } from "./client";
export { apiErrorMessage, ERROR_CODE_MESSAGES, ERROR_CODES } from "./error-messages";
export type { ErrorCode } from "./error-messages";
// mock 차단 토글 — 정본은 ./mock/data. queries.ts의 mock 분기·테스트가 "./index" 경로로 소비(경로 안정).
export { mockSetBlocked } from "./mock/data";

// USE_API — 빌드타임 상수. NEXT_PUBLIC_API_URL을 번들러가 리터럴로 인라인하므로 이 분기는 DCE 가능
// → 라이브 빌드에서 mock 폴백(./mock/data)이 클라이언트 번들에서 트리셰이킹된다(R6-W2C).
// 의미론은 기존 Boolean(config.apiUrl)과 동일(config.apiUrl = NEXT_PUBLIC_API_URL || "").
const USE_API = Boolean(process.env.NEXT_PUBLIC_API_URL);
interface RawCreator {
  id: string;
  handle: string;
  name: string;
  bio: string;
  accent_color: string;
  avatar_url: string;
  cover_url: string;
  category: string;
  verified: boolean;
  followers: number;
  posts: number;
  following: boolean;
  // 서버 CreatorOut.blocked(default false) — 단건 조회에서만 신뢰값. 목록엔 없을 수 있어 옵셔널.
  blocked?: boolean;
}
interface RawPost {
  id: string;
  creator_id: string;
  creator_name: string;
  creator_handle: string;
  verified: boolean;
  body: string;
  media_url: string;
  like_count: number;
  comment_count: number;
  liked: boolean;
  is_adult?: boolean;
  created_at: string;
}
interface RawComment {
  id: string;
  post_id: string;
  author: string;
  body: string;
  created_at: string;
}
interface RawProduct {
  id: string;
  creator_id: string | null;
  creator_name: string;
  // 서버 ProductOut.creator_handle(기본 "") — PDP/스토어의 크리에이터 프로필 링크용.
  // 검색 브리프(ProductBrief)엔 없고 빈 문자열일 수 있어 옵셔널 방어(없으면 링크 생략).
  creator_handle?: string | null;
  type: string;
  title: string;
  price: number;
  meta: string;
  media_url: string;
  description: string;
  options: string[];
  stock: number | null;
  sold_out: boolean;
  locked: boolean;
  is_adult?: boolean;
  // status는 오너 스코프(StudioProductOut) 전용 — 공개 ProductOut엔 없어 옵셔널.
  status?: string;
}
interface RawTier {
  id: string;
  creator_id: string | null;
  name: string;
  price: number;
  period: string;
  benefits: string[];
  badge: string;
  featured: boolean;
  sort_order: number;
}
/** /search 결과의 축약 상품(ProductBrief — creator_id/media_url 없음). */
interface RawProductBrief {
  id: string;
  type: string;
  title: string;
  price: number;
  meta: string;
}
interface RawSearch {
  creators: RawCreator[];
  products: RawProductBrief[];
  next_offset?: number | null;
}
// --- B4 쓰기/커머스 wire 계약(snake_case) ------------------------------------
interface RawOrderItem {
  product_id: string | null;
  title: string;
  type: string;
  option: string;
  price: number;
  qty: number;
}
interface RawRefund {
  status: string;
  reason: string;
}
/** 배송지 스냅샷 wire(OrderShippingOut) — 배송 상품 주문 조회에만 임베드. */
interface RawOrderShipping {
  recipient_name: string;
  recipient_phone: string;
  postal_code: string;
  address1: string;
  address2: string;
}
interface RawOrder {
  id: string;
  status: string;
  created_at: string;
  items: RawOrderItem[];
  subtotal: number;
  shipping: number;
  // shipping_fee는 model 정합 명시 별칭(shipping과 동일 값) — 있으면 우선, 없으면 shipping 폴백.
  shipping_fee?: number;
  total: number;
  creator_name: string | null;
  shipping_address?: RawOrderShipping | null;
  refund: RawRefund | null;
}
interface RawSubscription {
  id: string;
  creator_id: string | null;
  creator_name: string;
  creator_handle: string;
  tier_id: string | null;
  tier_name: string;
  price: number;
  period: string;
  status: string;
  next_billing_date: string;
  cancel_scheduled: boolean;
}
interface RawNotification {
  id: string;
  kind: string;
  title: string;
  href: string;
  read: boolean;
  created_at: string;
}
// --- 게이트 기능(R3): 스튜디오 카탈로그 쓰기·결제수단 wire 계약(snake_case) ------
/** 오너 뷰 상품(StudioProductOut) — 관리 필드(status/is_adult/timestamp) 포함. */
interface RawStudioProduct {
  id: string;
  creator_id: string | null;
  type: string;
  title: string;
  price: number;
  meta: string;
  media_url: string;
  description: string;
  options: string[];
  stock: number | null;
  sold_out: boolean;
  locked: boolean;
  status: string;
  is_adult: boolean;
  created_at: string;
  // 비취소 주문 기준 누적 판매 수량(ASS-264). 카운트만 — 수익 금액 아님.
  sold: number;
}
/** 오너 뷰 티어(StudioTierOut) — active 관리 플래그 포함. */
interface RawStudioTier {
  id: string;
  creator_id: string | null;
  name: string;
  price: number;
  period: string;
  benefits: string[];
  badge: string;
  featured: boolean;
  active: boolean;
  sort_order: number;
  created_at: string;
  // status=active 구독 수(ASS-264). 카운트만 — 수익 금액 아님.
  subscribers: number;
}
/** 저장된 결제수단(SavedPaymentMethod wire) — brand+last4만(PAN 미보관). */
interface RawPaymentMethod {
  id: string;
  brand: string;
  last4: string;
  is_primary: boolean;
  created_at: string;
}
/** 스튜디오 대시보드 실 카운트 wire(StudioStatsOut) — 전부 정수 카운트(금액 필드 없음·정산 게이트). */
interface RawStudioStats {
  followers: number;
  posts: number;
  products: number;
  products_selling: number;
  orders: number;
  subscribers: number;
}
/** 소셜 토글 응답(카운트 정정용). */
export interface FollowResult {
  following: boolean;
  followers: number;
}
export interface LikeResult {
  liked: boolean;
  like_count: number;
}
/** 신고 접수 응답. */
export interface ReportResult {
  safetyReportId: string;
  status: string;
  createdAt: string;
}
/** 차단 토글 응답(서버 BlockOut — 클라 상태 정정용). */
export interface BlockResult {
  blocked: boolean;
  creatorId: string;
}
/** 설정 차단 목록 wire(BlockedCreatorOut). */
interface RawBlockedCreator {
  creator_id: string;
  name: string;
  handle: string;
}
const mapBlockedCreator = (b: RawBlockedCreator): BlockedCreator => ({
  creatorId: b.creator_id,
  name: b.name,
  handle: b.handle,
});

/** ISO 시각 → 상대 라벨(방금 / N분·시간·일 전 / 날짜). */
function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Date.now() - then;
  const min = Math.floor(diff / 60000);
  const hr = Math.floor(diff / 3600000);
  const day = Math.floor(diff / 86400000);
  if (min < 1) return "방금";
  if (hr < 1) return `${min}분 전`;
  if (day < 1) return `${hr}시간 전`;
  if (day < 7) return `${day}일 전`;
  return new Date(iso).toLocaleDateString("ko-KR");
}

const mapCreator = (c: RawCreator): Creator => ({
  id: c.id,
  name: c.name,
  handle: c.handle,
  bio: c.bio || undefined,
  accentColor: c.accent_color || undefined,
  avatarUrl: c.avatar_url || undefined,
  coverUrl: c.cover_url || undefined,
  followers: c.followers,
  posts: c.posts,
  verified: c.verified,
  category: c.category || undefined,
  following: c.following,
  blocked: c.blocked,
});
const mapPost = (p: RawPost): Post => ({
  id: p.id,
  creatorId: p.creator_id,
  creatorName: p.creator_name,
  creatorMeta: `@${p.creator_handle} · ${relativeTime(p.created_at)}`,
  verified: p.verified,
  body: p.body || undefined,
  mediaUrl: p.media_url || undefined,
  likeCount: p.like_count,
  commentCount: p.comment_count,
  liked: p.liked,
  isAdult: p.is_adult || undefined,
});
const mapComment = (c: RawComment): Comment => ({
  id: c.id,
  postId: c.post_id,
  author: c.author,
  body: c.body,
  createdAt: relativeTime(c.created_at),
});
const mapProduct = (p: RawProduct): Product => ({
  id: p.id,
  creatorId: p.creator_id ?? undefined,
  creatorName: p.creator_name || undefined,
  type: p.type as Product["type"],
  title: p.title,
  price: p.price,
  creatorHandle: p.creator_handle || undefined,
  meta: p.meta || undefined,
  mediaUrl: p.media_url || undefined,
  // 확장 필드 — 품절/잠금/옵션 UI가 라이브에서도 동작해야 한다(누락 시 서버 422가 최후 방어막이 됨).
  description: p.description || undefined,
  options: p.options?.length ? p.options : undefined,
  stock: p.stock ?? undefined,
  soldOut: p.sold_out || undefined,
  locked: p.locked || undefined,
  isAdult: p.is_adult || undefined,
  status: p.status || undefined,
});
const mapTier = (t: RawTier): MembershipTier => ({
  id: t.id,
  creatorId: t.creator_id ?? undefined,
  name: t.name,
  price: t.price,
  period: t.period,
  benefits: t.benefits,
  badge: t.badge || undefined,
  featured: t.featured,
});
const mapProductBrief = (p: RawProductBrief): Product => ({
  id: p.id,
  type: p.type as Product["type"],
  title: p.title,
  price: p.price,
  meta: p.meta || undefined,
});

/** ISO 시각 → 표시용 날짜(YYYY-MM-DD). 비정상 값은 원문 유지. */
function dateLabel(iso: string): string {
  return /^\d{4}-\d{2}-\d{2}/.test(iso) ? iso.slice(0, 10) : iso;
}
/** 서버 환불 상태 → 웹 표기(accepted→approved, reviewing/그 외→requested). */
function mapRefundStatus(s: string): RefundStatus {
  if (s === "accepted") return "approved";
  if (s === "rejected") return "rejected";
  return "requested";
}
const mapOrderItem = (it: RawOrderItem): OrderItem => ({
  productId: it.product_id ?? "",
  title: it.title,
  type: it.type as OrderItem["type"],
  option: it.option || undefined,
  price: it.price,
  qty: it.qty,
});
const mapShipping = (s: RawOrderShipping): ShippingAddress => ({
  recipientName: s.recipient_name,
  recipientPhone: s.recipient_phone,
  postalCode: s.postal_code,
  address1: s.address1,
  address2: s.address2,
});
const mapOrder = (o: RawOrder): Order => ({
  id: o.id,
  createdAt: dateLabel(o.created_at),
  status: o.status as OrderStatus,
  items: o.items.map(mapOrderItem),
  subtotal: o.subtotal,
  // shipping_fee(model 정합 별칭) 우선, 없으면 기존 shipping 필드 폴백(둘은 동일 값).
  shipping: o.shipping_fee ?? o.shipping,
  total: o.total,
  creatorName: o.creator_name ?? undefined,
  shippingAddress: o.shipping_address ? mapShipping(o.shipping_address) : undefined,
  refund: o.refund
    ? { status: mapRefundStatus(o.refund.status), reason: o.refund.reason || undefined }
    : undefined,
});
const mapSubscription = (s: RawSubscription): Subscription => ({
  id: s.id,
  creatorId: s.creator_id ?? "",
  creatorName: s.creator_name,
  creatorHandle: s.creator_handle,
  tierId: s.tier_id ?? undefined,
  tierName: s.tier_name,
  price: s.price,
  period: s.period,
  nextBillingDate: dateLabel(s.next_billing_date),
  status: s.status === "cancelled" ? "cancelled" : "active",
  cancelScheduled: s.cancel_scheduled,
});
const NOTIFICATION_KINDS: NotificationKind[] = ["like", "comment", "follow", "order", "system"];
const mapNotification = (n: RawNotification): Notification => {
  const kind = NOTIFICATION_KINDS.includes(n.kind as NotificationKind) ? (n.kind as NotificationKind) : "system";
  const t = new Date(n.created_at).getTime();
  // 24시간 이내는 "오늘" 그룹, 그 외는 "이전"(서버는 group 필드를 주지 않아 파생).
  const group: Notification["group"] =
    !Number.isNaN(t) && Date.now() - t < 86400000 ? "today" : "earlier";
  return {
    id: n.id,
    kind,
    title: n.title,
    time: relativeTime(n.created_at),
    group,
    href: n.href || undefined,
    read: n.read,
  };
};

const PRODUCT_STATUSES: readonly ProductStatus[] = ["selling", "soldout", "draft", "hidden"];
/**
 * 오너 상품 매핑 — sold는 서버가 집계한 비취소 주문 기준 누적 판매 수량(ASS-264, 카운트만·수익
 * 금액 아님). updatedAt은 생성 시각 파생.
 */
const mapStudioProduct = (p: RawStudioProduct): StudioProduct => ({
  id: p.id,
  type: p.type as StudioProduct["type"],
  title: p.title,
  price: p.price,
  status: (PRODUCT_STATUSES as readonly string[]).includes(p.status) ? (p.status as ProductStatus) : "draft",
  sold: p.sold,
  stock: p.stock ?? null,
  updatedAt: relativeTime(p.created_at),
});
/** 오너 티어 매핑 — subscribers는 서버가 집계한 활성(status=active) 구독자 수(ASS-264, 카운트만). */
const mapStudioTier = (t: RawStudioTier): StudioTier => ({
  id: t.id,
  name: t.name,
  price: t.price,
  benefits: t.benefits,
  subscribers: t.subscribers,
  active: t.active,
});
const mapPaymentMethod = (m: RawPaymentMethod): SavedPaymentMethod => ({
  id: m.id,
  brand: m.brand,
  last4: m.last4,
  isPrimary: m.is_primary,
  createdAt: m.created_at,
});
/** 스튜디오 스탯 매핑 — snake→camel(products_selling→productsSelling). 전부 정수 카운트(금액 없음). */
const mapStudioStats = (s: RawStudioStats): StudioStats => ({
  followers: s.followers,
  posts: s.posts,
  products: s.products,
  productsSelling: s.products_selling,
  orders: s.orders,
  subscribers: s.subscribers,
});

// --- mock 폴백 데이터 → ./mock/data 로 분리(R6-W2C 번들 격리). USE_API=false 폴백에서만 참조. ------

// --- 커서 페이지네이션(R4-W1): 커서 인지 fetcher --------------------------------
/**
 * 커서 페이지 — 뷰/훅이 소비하는 언랩 형태(camelCase). 서버 `Paginated<T>`(next_cursor)에서
 * items를 매핑하고 next_cursor→nextCursor로 좁힌다. 마지막 페이지·mock 폴백은 nextCursor=undefined.
 */
export interface Page<T> {
  items: T[];
  nextCursor?: string;
}

/** cursor + 추가 파라미터(creator_id 등)를 병합해 쿼리스트링 구성(빈 값은 생략). */
function pageQuery(cursor?: string, ...extra: (string | false | undefined)[]): string {
  const parts = [...extra, cursor ? `cursor=${encodeURIComponent(cursor)}` : undefined].filter(
    (p): p is string => Boolean(p),
  );
  return parts.length ? `?${parts.join("&")}` : "";
}

/** 서버 Paginated 응답 → Page(매퍼 적용 + next_cursor 정규화). */
function toPage<R, T>(raw: Paginated<R>, map: (r: R) => T): Page<T> {
  return { items: raw.items.map(map), nextCursor: raw.next_cursor ?? undefined };
}

// --- 런타임 capability 플래그(ASS-287) — 서버 설정 단일 출처 ------------------
/** 런타임 capability 플래그(camelCase) — 게이트된 흐름의 개방 여부. 서버 CapabilitiesResponse 미러. */
export interface Capabilities {
  /** 배송(굿즈) 결제 흐름 개방 여부(서버 ENABLE_SHIPPING_CHECKOUT). false면 배송 PII 폼에 도달시키지 않는다. */
  shippingCheckoutAvailable: boolean;
  /** mock 결제 흐름 개방 여부(서버 ENABLE_MOCK_PAYMENT). */
  paymentAvailable: boolean;
}
interface RawCapabilities {
  shipping_checkout_available: boolean;
  payment_available: boolean;
}
/**
 * 런타임 capability — `GET /api/capabilities`(서버 설정 단일 출처, 웹이 플래그를 별도로 복제하지
 * 않는다 → 서버와 드리프트 방지). mock 폴백(USE_API=false)은 게이트 닫힘으로 취급(fail-closed) —
 * 실제로 일어날 수 없는 배송 결제를 mock에서 노출하지 않는다(방어심층).
 */
export async function getCapabilities(): Promise<Capabilities> {
  if (USE_API) {
    const raw = await apiFetch<RawCapabilities>("/capabilities");
    return { shippingCheckoutAvailable: raw.shipping_checkout_available, paymentAvailable: raw.payment_available };
  }
  return { shippingCheckoutAvailable: false, paymentAvailable: false };
}

// --- 도메인 함수 (apiUrl 설정 시 실 B2 API, 아니면 mock 폴백) ----------------
export async function getCreators(): Promise<Creator[]> {
  if (USE_API) return (await apiFetch<Paginated<RawCreator>>("/creators")).items.map(mapCreator);
  return CREATORS;
}
/**
 * mock 크리에이터 서버 랭킹 근사(E11) — popular=팔로워 desc, new=배열 역순(최근 합류 근사, 기존
 * 클라 `.reverse()`와 동일 의미론), recommended=팔로워 desc(목업엔 가입시각이 없어 동률 없음 →
 * 서버 recommended(-followers,-created_at)와 동일 결과). sort 미지정은 원본 순서(handle 커서).
 */
function sortCreatorsMock(sort?: CreatorSort): Creator[] {
  if (sort === "popular" || sort === "recommended") return [...CREATORS].sort((a, b) => b.followers - a.followers);
  if (sort === "new") return [...CREATORS].reverse();
  return CREATORS;
}
/**
 * 크리에이터 커서 페이지 — 디스커버리 무한 로드(21번째+ 도달). `sort` 지정 시 서버 랭킹 단일
 * 페이지(next_cursor 없음 — popular/new/recommended). mock은 단일 페이지(nextCursor 없음).
 */
export async function getCreatorsPage(cursor?: string, sort?: CreatorSort): Promise<Page<Creator>> {
  if (USE_API) {
    const q = pageQuery(cursor, sort && `sort=${encodeURIComponent(sort)}`);
    return toPage(await apiFetch<Paginated<RawCreator>>(`/creators${q}`), mapCreator);
  }
  return { items: sortCreatorsMock(sort) };
}
export async function getCreator(handle: string): Promise<Creator | undefined> {
  if (USE_API) {
    try {
      return mapCreator(await apiFetch<RawCreator>(`/creators/${encodeURIComponent(handle)}`));
    } catch (e) {
      // 404(없음) + 422(잘못된 식별자) 모두 notFound()로 → 에러 페이지 대신 404.
      if (e instanceof ApiError && (e.status === 404 || e.status === 422)) return undefined;
      throw e;
    }
  }
  // mock: 로컬 차단 상태를 반영(단건 blocked 코히어런스 — 정적 CREATORS는 불변 유지).
  const found = CREATORS.find((c) => c.handle === handle);
  return found ? { ...found, blocked: MOCK_BLOCKED.has(found.id) } : undefined;
}
export async function getProducts(creatorId?: string): Promise<Product[]> {
  if (USE_API) {
    const q = creatorId ? `?creator_id=${encodeURIComponent(creatorId)}` : "";
    return (await apiFetch<Paginated<RawProduct>>(`/products${q}`)).items.map(mapProduct);
  }
  return creatorId ? PRODUCTS.filter((p) => p.creatorId === creatorId) : PRODUCTS;
}
/** 상품 커서 페이지 — 스토어·디스커버리 무한 로드. mock은 단일 페이지(nextCursor 없음). */
export async function getProductsPage(creatorId?: string, cursor?: string): Promise<Page<Product>> {
  if (USE_API) {
    const q = pageQuery(cursor, creatorId && `creator_id=${encodeURIComponent(creatorId)}`);
    return toPage(await apiFetch<Paginated<RawProduct>>(`/products${q}`), mapProduct);
  }
  return { items: creatorId ? PRODUCTS.filter((p) => p.creatorId === creatorId) : PRODUCTS };
}
export async function getMembershipTiers(creatorId?: string): Promise<MembershipTier[]> {
  if (USE_API) {
    const q = creatorId ? `?creator_id=${encodeURIComponent(creatorId)}` : "";
    return (await apiFetch<RawTier[]>(`/tiers${q}`)).map(mapTier);
  }
  return creatorId ? TIERS.filter((t) => t.creatorId === creatorId) : TIERS;
}
/** creatorId 지정 시 해당 크리에이터 포스트, 미지정 시 전체. */
export async function getPosts(creatorId?: string): Promise<Post[]> {
  if (USE_API) {
    const q = creatorId ? `?creator_id=${encodeURIComponent(creatorId)}` : "";
    return (await apiFetch<Paginated<RawPost>>(`/posts${q}`)).items.map(mapPost);
  }
  return creatorId ? POSTS.filter((p) => p.creatorId === creatorId) : POSTS;
}
/** 포스트 커서 페이지 — 크리에이터 포스트 무한 로드. mock은 단일 페이지. */
export async function getPostsPage(creatorId?: string, cursor?: string): Promise<Page<Post>> {
  if (USE_API) {
    const q = pageQuery(cursor, creatorId && `creator_id=${encodeURIComponent(creatorId)}`);
    return toPage(await apiFetch<Paginated<RawPost>>(`/posts${q}`), mapPost);
  }
  return { items: creatorId ? POSTS.filter((p) => p.creatorId === creatorId) : POSTS };
}
/**
 * 스튜디오 오너 포스트 커서 페이지 — GET /studio/posts(fan_auth 오너 스코프). 공개 `/posts`와 달리
 * 소비자 게이트(19+ 숨김)가 적용되지 않아 오너가 자신의 draft·19+ 포스트를 전부 본다.
 * 401·403 모두 그대로 전파한다 — client.ts가 이미 401 refresh-and-retry를 하므로 여기 도달한
 * 401은 회복 불가 세션(만료-잔존 쿠키)이다. 빈 페이지로 삼키면 "발행 포스트 없음"으로 오표시되므로,
 * 호출측(StudioPostsPage)이 401=재로그인 안내·403(OwnerRequired)=크리에이터 안내로 분기 렌더한다.
 * mock=데모 오너(c1: 별빛 일러스트) 목록.
 */
export async function getStudioPostsPage(cursor?: string): Promise<Page<Post>> {
  if (USE_API) {
    return toPage(await apiFetch<Paginated<RawPost>>(`/studio/posts${pageQuery(cursor)}`), mapPost);
  }
  return { items: POSTS.filter((p) => p.creatorId === "c1") };
}
/** 피드 — B2 `/feed` 소비(익명=최신 전체). B3 개인화(팔로잉) 피드의 배선 지점. */
export async function getFeed(): Promise<Post[]> {
  if (USE_API) return (await apiFetch<Paginated<RawPost>>("/feed")).items.map(mapPost);
  return POSTS;
}
/** 피드 커서 페이지 — 무한 로드. mock은 단일 페이지. */
export async function getFeedPage(cursor?: string): Promise<Page<Post>> {
  if (USE_API) return toPage(await apiFetch<Paginated<RawPost>>(`/feed${pageQuery(cursor)}`), mapPost);
  return { items: POSTS };
}
const SEARCH_LIMIT_DEFAULT = 10;
const SEARCH_LIMIT_MAX = 50;

/** mock 크리에이터 매치 랭크 — 서버 match_rank(이름 완전일치→접두→포함→핸들→기타)를 근사. */
function creatorMatchRank(c: Creator, t: string): number {
  const name = c.name.toLowerCase();
  if (name === t) return 0;
  if (name.startsWith(t)) return 1;
  if (name.includes(t)) return 2;
  if (c.handle.toLowerCase().includes(t)) return 3;
  return 4; // bio/category만 매치
}
/** mock 상품 매치 랭크 — 서버 match_rank(제목 접두→포함→기타)를 근사. */
function productMatchRank(p: Product, t: string): number {
  const title = p.title.toLowerCase();
  if (title.startsWith(t)) return 0;
  if (title.includes(t)) return 1;
  return 2;
}
/**
 * 검색 mock 폴백 — 서버 의미론 미러: 크리에이터는 name/handle/bio/category, 상품은
 * title/meta/description 다필드 substring 매칭 + 랭킹(best match 먼저) + limit/offset 페이지네이션.
 */
function mockSearch(term: string, limit: number | undefined, offset: number): SearchResult {
  const t = term.toLowerCase();
  const size = Math.max(1, Math.min(limit ?? SEARCH_LIMIT_DEFAULT, SEARCH_LIMIT_MAX));
  const matchedCreators = CREATORS.filter(
    (c) =>
      c.name.toLowerCase().includes(t) ||
      c.handle.toLowerCase().includes(t) ||
      (c.bio?.toLowerCase().includes(t) ?? false) ||
      (c.category?.toLowerCase().includes(t) ?? false),
  ).sort((a, b) => creatorMatchRank(a, t) - creatorMatchRank(b, t) || b.followers - a.followers);
  const matchedProducts = PRODUCTS.filter(
    (p) =>
      p.title.toLowerCase().includes(t) ||
      (p.meta?.toLowerCase().includes(t) ?? false) ||
      (p.description?.toLowerCase().includes(t) ?? false),
  ).sort((a, b) => productMatchRank(a, t) - productMatchRank(b, t));
  const more = matchedCreators.length > offset + size || matchedProducts.length > offset + size;
  return {
    creators: matchedCreators.slice(offset, offset + size),
    products: matchedProducts.slice(offset, offset + size),
    nextOffset: more ? offset + size : null,
  };
}
/**
 * 검색 — B2 `/search?q=&limit=&offset=` 소비(랭킹 + 페이지네이션). mock 폴백은 서버 의미론을 미러.
 */
export async function getSearch(q: string, opts: { limit?: number; offset?: number } = {}): Promise<SearchResult> {
  const term = q.trim();
  if (!term) return { creators: [], products: [] };
  const offset = Math.max(0, opts.offset ?? 0);
  if (USE_API) {
    const params = [`q=${encodeURIComponent(term)}`];
    if (opts.limit != null) params.push(`limit=${opts.limit}`);
    if (offset) params.push(`offset=${offset}`);
    const raw = await apiFetch<RawSearch>(`/search?${params.join("&")}`);
    return {
      creators: raw.creators.map(mapCreator),
      products: raw.products.map(mapProductBrief),
      nextOffset: raw.next_offset ?? null,
    };
  }
  return mockSearch(term, opts.limit, offset);
}
export async function getPost(id: string): Promise<Post | undefined> {
  if (USE_API) {
    try {
      return mapPost(await apiFetch<RawPost>(`/posts/${encodeURIComponent(id)}`));
    } catch (e) {
      // 404(없음) + 422(잘못된 UUID) 모두 notFound()로 → 에러 페이지 대신 404.
      if (e instanceof ApiError && (e.status === 404 || e.status === 422)) return undefined;
      throw e;
    }
  }
  return POSTS.find((p) => p.id === id);
}
export async function getComments(postId: string): Promise<Comment[]> {
  if (USE_API) {
    const path = `/posts/${encodeURIComponent(postId)}/comments`;
    return (await apiFetch<Paginated<RawComment>>(path)).items.map(mapComment);
  }
  return COMMENTS.filter((c) => c.postId === postId);
}
/** 댓글 커서 페이지 — 포스트 상세 무한 로드. mock은 단일 페이지. */
export async function getCommentsPage(postId: string, cursor?: string): Promise<Page<Comment>> {
  if (USE_API) {
    const path = `/posts/${encodeURIComponent(postId)}/comments${pageQuery(cursor)}`;
    return toPage(await apiFetch<Paginated<RawComment>>(path), mapComment);
  }
  return { items: COMMENTS.filter((c) => c.postId === postId) };
}

/**
 * 단일 상품 — USE_API면 `GET /products/{id}`(ProductOut) 단건 조회(404/422→undefined),
 * 아니면 목록에서 id로 find 폴백. 확장 필드(options/description/stock/soldOut/locked/creatorName)는
 * 서버 계약(B4)에 포함되어 라이브·mock 양쪽에서 동일하게 흐른다.
 */
export async function getProduct(id: string): Promise<Product | undefined> {
  if (USE_API) {
    try {
      return mapProduct(await apiFetch<RawProduct>(`/products/${encodeURIComponent(id)}`));
    } catch (e) {
      // 404(없음) + 422(잘못된 식별자) 모두 undefined로 → notFound() 계약.
      if (e instanceof ApiError && (e.status === 404 || e.status === 422)) return undefined;
      throw e;
    }
  }
  const list = await getProducts();
  return list.find((p) => p.id === id);
}

/** 주문 목록 — USE_API면 커서 페이지 소비, 아니면 mock. SSR 401(비로그인)은 빈 목록. */
export async function getOrders(): Promise<Order[]> {
  if (USE_API) {
    try {
      return (await apiFetch<Paginated<RawOrder>>("/orders")).items.map(mapOrder);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return [];
      throw e;
    }
  }
  return ORDERS;
}
/** 주문 커서 페이지 — 무한 로드. 401(비로그인)은 빈 단일 페이지. mock은 단일 페이지. */
export async function getOrdersPage(cursor?: string): Promise<Page<Order>> {
  if (USE_API) {
    try {
      return toPage(await apiFetch<Paginated<RawOrder>>(`/orders${pageQuery(cursor)}`), mapOrder);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return { items: [] };
      throw e;
    }
  }
  return { items: ORDERS };
}
/** 단일 주문 — USE_API면 실 조회. 미지의 id/비로그인은 undefined(notFound 계약). */
export async function getOrder(id: string): Promise<Order | undefined> {
  if (USE_API) {
    try {
      return mapOrder(await apiFetch<RawOrder>(`/orders/${encodeURIComponent(id)}`));
    } catch (e) {
      if (e instanceof ApiError && (e.status === 404 || e.status === 422 || e.status === 401)) return undefined;
      throw e;
    }
  }
  return ORDERS.find((o) => o.id === id);
}
/** 알림 목록 — USE_API면 커서 페이지 소비, 아니면 mock. SSR 401(비로그인)은 빈 목록. */
export async function getNotifications(): Promise<Notification[]> {
  if (USE_API) {
    try {
      return (await apiFetch<Paginated<RawNotification>>("/notifications")).items.map(mapNotification);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return [];
      throw e;
    }
  }
  return NOTIFICATIONS;
}
/** 알림 커서 페이지 — 무한 로드. 401(비로그인)은 빈 단일 페이지. mock은 단일 페이지. */
export async function getNotificationsPage(cursor?: string): Promise<Page<Notification>> {
  if (USE_API) {
    try {
      const raw = await apiFetch<Paginated<RawNotification>>(`/notifications${pageQuery(cursor)}`);
      return toPage(raw, mapNotification);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return { items: [] };
      throw e;
    }
  }
  return { items: NOTIFICATIONS };
}
/** 구독 목록 — USE_API면 실 조회(배열 응답), 아니면 mock. SSR 401(비로그인)은 빈 목록. */
export async function getSubscriptions(): Promise<Subscription[]> {
  if (USE_API) {
    try {
      return (await apiFetch<RawSubscription[]>("/subscriptions")).map(mapSubscription);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return [];
      throw e;
    }
  }
  return SUBSCRIPTIONS;
}
/** 내 차단 목록 — USE_API면 GET /fan/blocks, 아니면 mock 로컬 상태. 401(비로그인)은 빈 목록. */
export async function getBlocks(): Promise<BlockedCreator[]> {
  if (USE_API) {
    try {
      return (await apiFetch<RawBlockedCreator[]>("/fan/blocks")).map(mapBlockedCreator);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return [];
      throw e;
    }
  }
  return CREATORS.filter((c) => MOCK_BLOCKED.has(c.id)).map((c) => ({
    creatorId: c.id,
    name: c.name,
    handle: c.handle,
  }));
}

// --- 뮤테이션 API(실 호출 전용 — queries.ts가 USE_API로 분기해 호출) ----------
/** 팔로우 토글 — next=true PUT, false DELETE → {following, followers}. */
export function apiToggleFollow(handle: string, next: boolean): Promise<FollowResult> {
  return apiFetch<FollowResult>(`/creators/${encodeURIComponent(handle)}/follow`, {
    method: next ? "PUT" : "DELETE",
  });
}
/** 좋아요 토글 — next=true PUT, false DELETE → {liked, like_count}. */
export function apiToggleLike(id: string, next: boolean): Promise<LikeResult> {
  return apiFetch<LikeResult>(`/posts/${encodeURIComponent(id)}/like`, {
    method: next ? "PUT" : "DELETE",
  });
}
/** 댓글 작성 → 201 Comment. */
export async function apiAddComment(postId: string, body: string): Promise<Comment> {
  const raw = await apiFetch<RawComment>(`/posts/${encodeURIComponent(postId)}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
  return mapComment(raw);
}
/**
 * 주문 생성(mock 결제 확정 — 실 PG·금액이동 없음) → 201 Order.
 * 배송 상품(굿즈)이면 shipping(배송지)을 함께 전송한다 — 누락 시 서버 422 ShippingAddressRequired.
 */
export async function apiCreateOrder(input: {
  productId: string;
  qty: number;
  option?: string;
  shipping?: ShippingAddress;
}): Promise<Order> {
  const raw = await apiFetch<RawOrder>("/orders", {
    method: "POST",
    body: JSON.stringify({
      product_id: input.productId,
      qty: input.qty,
      option: input.option,
      shipping: input.shipping
        ? {
            recipient_name: input.shipping.recipientName,
            recipient_phone: input.shipping.recipientPhone,
            postal_code: input.shipping.postalCode,
            address1: input.shipping.address1,
            address2: input.shipping.address2,
          }
        : undefined,
    }),
  });
  return mapOrder(raw);
}
/** 주문 취소(paid/shipping) → Order. */
export async function apiCancelOrder(id: string): Promise<Order> {
  return mapOrder(await apiFetch<RawOrder>(`/orders/${encodeURIComponent(id)}/cancel`, { method: "POST" }));
}
/** 환불 신청(shipping/completed) → refund 임베드 포함 Order. */
export async function apiRequestRefund(input: { id: string; reason: string; detail?: string }): Promise<Order> {
  const raw = await apiFetch<RawOrder>(`/orders/${encodeURIComponent(input.id)}/refund`, {
    method: "POST",
    body: JSON.stringify({ reason: input.reason, detail: input.detail }),
  });
  return mapOrder(raw);
}
/** 구독 시작(mock-paid) → 201 Subscription. */
export async function apiSubscribe(tierId: string): Promise<Subscription> {
  const raw = await apiFetch<RawSubscription>("/subscriptions", {
    method: "POST",
    body: JSON.stringify({ tier_id: tierId }),
  });
  return mapSubscription(raw);
}
/** 구독 해지(말일 해지 — status=active 유지 + cancel_scheduled) → Subscription. */
export async function apiCancelSubscription(id: string): Promise<Subscription> {
  return mapSubscription(
    await apiFetch<RawSubscription>(`/subscriptions/${encodeURIComponent(id)}/cancel`, { method: "POST" }),
  );
}
/**
 * 구독 티어 전환(업/다운그레이드) — PATCH /subscriptions/{id} {tier_id} → Subscription.
 * 같은 크리에이터의 active 티어만 가능(다른 크리에이터/비활성/미지 티어=422 TierNotFound),
 * 비활성 구독은 전환 불가(422 SubscriptionNotActive), 현재 티어로의 전환은 200 no-op(멱등).
 */
export async function apiChangeSubscriptionTier(id: string, tierId: string): Promise<Subscription> {
  return mapSubscription(
    await apiFetch<RawSubscription>(`/subscriptions/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ tier_id: tierId }),
    }),
  );
}
/** 알림 읽음 → Notification. */
export async function apiMarkNotificationRead(id: string): Promise<Notification> {
  return mapNotification(
    await apiFetch<RawNotification>(`/notifications/${encodeURIComponent(id)}/read`, { method: "POST" }),
  );
}
/** 알림 모두 읽음 → 갱신 건수. */
export function apiMarkAllNotificationsRead(): Promise<{ updated: number }> {
  return apiFetch<{ updated: number }>("/notifications/read-all", { method: "POST" });
}
/** 팬 신고 접수(운영자용 /safety/reports 아님) → 접수 결과. */
export async function apiReport(input: { reportType: string; narrative?: string }): Promise<ReportResult> {
  const raw = await apiFetch<{ safety_report_id: string; status: string; created_at: string }>(
    "/safety/fan-reports",
    { method: "POST", body: JSON.stringify({ report_type: input.reportType, narrative: input.narrative }) },
  );
  return { safetyReportId: raw.safety_report_id, status: raw.status, createdAt: raw.created_at };
}
/**
 * 크리에이터 차단 — POST /fan/blocks {creator_id} → {blocked, creator_id}(멱등).
 * 부수효과: 서버가 자동 언팔로우(팔로우 파생 노출 제거). 404=BlockTargetNotFound.
 */
export async function apiBlockCreator(creatorId: string): Promise<BlockResult> {
  const raw = await apiFetch<{ blocked: boolean; creator_id: string }>("/fan/blocks", {
    method: "POST",
    body: JSON.stringify({ creator_id: creatorId }),
  });
  return { blocked: raw.blocked, creatorId: raw.creator_id };
}
/** 크리에이터 차단 해제 — DELETE /fan/blocks/{creator_id} → {blocked, creator_id}(멱등). */
export async function apiUnblockCreator(creatorId: string): Promise<BlockResult> {
  const raw = await apiFetch<{ blocked: boolean; creator_id: string }>(
    `/fan/blocks/${encodeURIComponent(creatorId)}`,
    { method: "DELETE" },
  );
  return { blocked: raw.blocked, creatorId: raw.creator_id };
}
/** 포스트 발행(크리에이터 오너만 — 403 시 안내) → 201 Post. is_adult=19+ 성인 등급(서버가 노출 통제). */
export async function apiPublishPost(input: { body: string; mediaUrl?: string; isAdult?: boolean }): Promise<Post> {
  const raw = await apiFetch<RawPost>("/posts", {
    method: "POST",
    body: JSON.stringify({ body: input.body, media_url: input.mediaUrl, is_adult: input.isAdult ?? false }),
  });
  return mapPost(raw);
}
/** 포스트 부분 수정 입력(W1A: PATCH /posts/{id}) — 제공한 필드만 반영. */
export interface PostUpdate {
  body?: string;
  mediaUrl?: string;
  isAdult?: boolean;
}
/**
 * 포스트 수정 — PATCH /posts/{id}(body/media_url/is_adult 부분 수정). 오너만 가능하며
 * 비오너/미지 id는 서버가 404(no-leak). undefined 필드는 JSON.stringify가 제거 → 서버 무변경.
 */
export async function apiUpdatePost(id: string, patch: PostUpdate): Promise<Post> {
  const raw = await apiFetch<RawPost>(`/posts/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify({ body: patch.body, media_url: patch.mediaUrl, is_adult: patch.isAdult }),
  });
  return mapPost(raw);
}
/** 포스트 삭제 — DELETE /posts/{id}. 오너만 가능(비오너/미지 id는 404 no-leak). */
export async function apiDeletePost(id: string): Promise<void> {
  await apiFetch<{ status: string }>(`/posts/${encodeURIComponent(id)}`, { method: "DELETE" });
}

// --- R12: 이미지 업로드(포스트·상품·아바타 media_url 소스) ----------------------
/**
 * 이미지 업로드 — USE_API면 `POST /api/uploads`에 multipart(`file` 필드)로 전송하고 서버가 검증·저장 후
 * 반환하는 `{url}`(=`/media/uploads/<uuid>.<ext>`)을 그대로 media_url로 쓴다. apiFetch가 FormData 바디를
 * 감지하면 JSON Content-Type을 생략해 boundary가 살아있고, 쿠키/CSRF/401 재발급은 다른 뮤테이션과 동일 적용된다.
 * 실패는 서버 `{detail, code}`가 담긴 ApiError로 전파(415·413·422·503) → 호출측이 apiErrorMessage로 안내한다.
 *
 * mock 폴백(USE_API=false)은 실 업로드 없이 로컬 objectURL(미리보기용)만 반환한다 — 번들 격리 규율상
 * 라이브 빌드에선 이 분기가 DCE되고, mock 발행(apiPublishPost)도 실제 저장이 없어 objectURL로 충분하다.
 */
export async function apiUpload(file: File): Promise<{ url: string }> {
  if (USE_API) {
    const form = new FormData();
    form.append("file", file);
    return apiFetch<{ url: string }>("/uploads", { method: "POST", body: form });
  }
  // mock: 실 저장 없이 미리보기용 URL. objectURL 미가용(테스트/SSR 등)이면 플레이스홀더로 폴백.
  const url =
    typeof URL !== "undefined" && typeof URL.createObjectURL === "function"
      ? URL.createObjectURL(file)
      : "/media/uploads/mock-placeholder.png";
  return { url };
}

// --- 게이트 기능(R3): KYC 본인인증 -------------------------------------------
/**
 * 본인인증 시작(mock) — 서버 verifier 미배선 시 503. 성공은 pending 전이만 기록(PII 무전송).
 * ※실 provider(PASS/NICE/KCB) 연동은 명시적 게이트(대표·법무).
 */
export function apiStartVerify(): Promise<void> {
  return apiFetch<void>("/fan/verify/start", { method: "POST" });
}
/** 본인인증 확인(mock) → 파생 플래그만 반환(주민번호/CI/DI/생년월일 미수신·미저장). */
export async function apiConfirmVerify(): Promise<{ adultVerified: boolean; kycStatus: string }> {
  const raw = await apiFetch<{ adult_verified: boolean; kyc_status: string }>("/fan/verify/confirm", {
    method: "POST",
  });
  return { adultVerified: raw.adult_verified, kycStatus: raw.kyc_status };
}

// --- 게이트 기능(R3): 계정 수정 ----------------------------------------------
/** 내 프로필 수정 — nickname만(이메일/전화는 재인증 게이트). 세션 무효화는 호출측(useUpdateMe). */
export async function apiUpdateMe(nickname: string): Promise<void> {
  await apiFetch("/fan/me", { method: "PATCH", body: JSON.stringify({ nickname }) });
}

// --- R4-W5: 스튜디오 대시보드 실 카운트(오너 스코프) -------------------------
/**
 * 스튜디오 대시보드 실 카운트 — USE_API면 GET /studio/stats(StudioStatsOut) 소비.
 * 401(비로그인)/403(OwnerRequired, 비크리에이터)은 null(방어적 — 호출측이 빈 상태/안내 렌더).
 * mock 폴백은 결정적 카운트(STUDIO_STATS). 서버 계약에 수익/금액은 없다(정산 게이트).
 */
export async function getStudioStats(): Promise<StudioStats | null> {
  if (USE_API) {
    try {
      return mapStudioStats(await apiFetch<RawStudioStats>("/studio/stats"));
    } catch (e) {
      // 비크리에이터(403)·비로그인(401)은 통계 없음 → null(카운트를 0으로 날조하지 않는다).
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) return null;
      throw e;
    }
  }
  return STUDIO_STATS;
}

// --- ASS-289(#5): 스튜디오 재무(정산·애널리틱스) 데모 데이터 접근 ------------------
export type { SettlementRow, AnalyticsPoint } from "@/lib/studio-mock-finance";
/**
 * 정산 데모 행 — 서버가 정산/수익 금액을 제공하는 계약이 없으므로(정산 게이트) 라이브(USE_API)에선
 * null을 반환한다(클라이언트가 금액을 날조하지 않는다 → 호출측이 "준비 중" 렌더). mock 폴백에서만
 * placeholder 정산표를 반환한다. 라이브 빌드에선 이 else 참조가 데드코드가 되어 studio-mock-finance가
 * 트리셰이킹된다(mock/data.ts와 동일 규율).
 */
export function getSettlementDemoRows(): SettlementRow[] | null {
  if (USE_API) return null;
  return SETTLEMENT_ROWS;
}
/**
 * 애널리틱스 데모 시계열 — 서버가 수익/구독자 시계열 계약을 제공하지 않으므로 라이브에선 null(→ "준비 중").
 * mock 폴백에서만 placeholder 시계열을 반환한다. 라이브 빌드에서 트리셰이킹되는 것은 위와 동일.
 */
export function getAnalyticsDemoSeries(): AnalyticsPoint[] | null {
  if (USE_API) return null;
  return ANALYTICS_SERIES;
}

// --- 게이트 기능(R3): 스튜디오 카탈로그 쓰기(오너 스코프) ---------------------
/** 오너 상품 목록 — 관리 필드 포함(draft/hidden·19+ 포함). 401/403(크리에이터 아님)은 빈 목록. */
export async function getStudioProducts(): Promise<StudioProduct[]> {
  if (USE_API) {
    try {
      return (await apiFetch<RawStudioProduct[]>("/studio/products")).map(mapStudioProduct);
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) return [];
      throw e;
    }
  }
  return STUDIO_PRODUCTS;
}
/** 상품 생성 입력(가격은 크리에이터 표시가 — 정산가 아님). */
export interface StudioProductCreate {
  type: StudioProduct["type"];
  title: string;
  price: number;
  description?: string;
  status?: ProductStatus;
}
/** 상품 수정 입력 — 제공한 필드만 반영(PATCH). */
export interface StudioProductUpdate {
  type?: StudioProduct["type"];
  title?: string;
  price?: number;
  status?: ProductStatus;
  stock?: number | null;
}
export async function apiCreateStudioProduct(input: StudioProductCreate): Promise<StudioProduct> {
  const raw = await apiFetch<RawStudioProduct>("/studio/products", {
    method: "POST",
    body: JSON.stringify({
      type: input.type,
      title: input.title,
      price: input.price,
      description: input.description ?? "",
      status: input.status ?? "draft",
    }),
  });
  return mapStudioProduct(raw);
}
export async function apiUpdateStudioProduct(id: string, patch: StudioProductUpdate): Promise<StudioProduct> {
  const raw = await apiFetch<RawStudioProduct>(`/studio/products/${encodeURIComponent(id)}`, {
    method: "PATCH",
    // undefined 필드는 JSON.stringify가 제거 → 미제공 필드는 서버에서 무변경.
    body: JSON.stringify({ type: patch.type, title: patch.title, price: patch.price, status: patch.status, stock: patch.stock }),
  });
  return mapStudioProduct(raw);
}
export async function apiDeleteStudioProduct(id: string): Promise<void> {
  await apiFetch<{ status: string }>(`/studio/products/${encodeURIComponent(id)}`, { method: "DELETE" });
}

/** 오너 티어 목록 — active/비활성 모두 포함. 401/403은 빈 목록. */
export async function getStudioTiers(): Promise<StudioTier[]> {
  if (USE_API) {
    try {
      return (await apiFetch<RawStudioTier[]>("/studio/tiers")).map(mapStudioTier);
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) return [];
      throw e;
    }
  }
  return STUDIO_TIERS;
}
export interface StudioTierCreate {
  name: string;
  price: number;
  benefits: string[];
}
export interface StudioTierUpdate {
  name?: string;
  price?: number;
  benefits?: string[];
  active?: boolean;
}
export async function apiCreateStudioTier(input: StudioTierCreate): Promise<StudioTier> {
  const raw = await apiFetch<RawStudioTier>("/studio/tiers", {
    method: "POST",
    body: JSON.stringify({ name: input.name, price: input.price, benefits: input.benefits }),
  });
  return mapStudioTier(raw);
}
export async function apiUpdateStudioTier(id: string, patch: StudioTierUpdate): Promise<StudioTier> {
  const raw = await apiFetch<RawStudioTier>(`/studio/tiers/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify({ name: patch.name, price: patch.price, benefits: patch.benefits, active: patch.active }),
  });
  return mapStudioTier(raw);
}
export async function apiDeleteStudioTier(id: string): Promise<void> {
  await apiFetch<{ status: string }>(`/studio/tiers/${encodeURIComponent(id)}`, { method: "DELETE" });
}

/** 스튜디오 프로필 수정(오너 스코프) → 갱신된 Creator. */
export interface StudioProfileUpdate {
  name?: string;
  bio?: string;
  avatarUrl?: string;
  coverUrl?: string;
  accentColor?: string;
  category?: string;
}
export async function apiUpdateStudioProfile(input: StudioProfileUpdate): Promise<Creator> {
  const raw = await apiFetch<RawCreator>("/studio/profile", {
    method: "PATCH",
    body: JSON.stringify({
      name: input.name,
      bio: input.bio,
      avatar_url: input.avatarUrl,
      cover_url: input.coverUrl,
      accent_color: input.accentColor,
      category: input.category,
    }),
  });
  return mapCreator(raw);
}

// --- 게이트 기능(R3): 결제수단(mock PG) --------------------------------------
/**
 * mock PG 토큰 — 실 PG SDK가 카드번호를 클라에서 토큰화하는 자리(자리표시).
 * ★PCI(R4): raw 카드번호(PAN)/CVC는 이 경로로 서버에 절대 전송되지 않는다. 서버는 토큰
 * 끝 4자리로 last4만 파생하고 나머지는 폐기한다.
 */
function mockPgToken(): string {
  const last4 = String(1000 + Math.floor(Math.random() * 9000));
  return `pg_mock_tok_${last4}`;
}
/** 내 결제수단 목록(최신순). 401(비로그인)은 빈 목록. */
export async function getPaymentMethods(): Promise<SavedPaymentMethod[]> {
  if (USE_API) {
    try {
      return (await apiFetch<RawPaymentMethod[]>("/fan/payment-methods")).map(mapPaymentMethod);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return [];
      throw e;
    }
  }
  return PAYMENT_METHODS;
}
/** 결제수단 등록 — brand + mock PG 토큰만 전송(raw PAN/CVC 미전송·PCI). */
export async function apiAddPaymentMethod(input: { brand: string; makePrimary?: boolean }): Promise<SavedPaymentMethod> {
  const raw = await apiFetch<RawPaymentMethod>("/fan/payment-methods", {
    method: "POST",
    body: JSON.stringify({ brand: input.brand, card_number: mockPgToken(), make_primary: input.makePrimary ?? false }),
  });
  return mapPaymentMethod(raw);
}
/** 기본 결제수단 지정 → 갱신된 결제수단. */
export async function apiSetPrimaryPaymentMethod(id: string): Promise<SavedPaymentMethod> {
  return mapPaymentMethod(
    await apiFetch<RawPaymentMethod>(`/fan/payment-methods/${encodeURIComponent(id)}/primary`, { method: "POST" }),
  );
}
/** 결제수단 삭제. */
export async function apiRemovePaymentMethod(id: string): Promise<void> {
  await apiFetch<{ status: string }>(`/fan/payment-methods/${encodeURIComponent(id)}`, { method: "DELETE" });
}
