/**
 * Assen 도메인 API — B2 백엔드 연동 (SDLC 09 B5).
 *
 * `config.apiUrl`(NEXT_PUBLIC_API_URL)가 설정되면 실 Django Ninja B2 API를 호출하고
 * snake_case→camelCase 매핑 + 커서 페이지 언랩을 수행한다. 미설정(빌드/CI/standalone)이면
 * 아래 mock으로 폴백 → `next build`(SSG)와 백엔드 없는 개발이 그대로 동작한다.
 * 계약 타입: openapi.json → schema.d.ts (openapi-typescript, `npm run gen:types`).
 */
import { config } from "@/lib/config";
import { apiFetch, ApiError } from "./client";
import type {
  Comment,
  Creator,
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
  Subscription,
  SearchResult,
} from "./types";

export * from "./types";
export { apiFetch, ApiError } from "./client";

const USE_API = Boolean(config.apiUrl);
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
interface RawOrder {
  id: string;
  status: string;
  created_at: string;
  items: RawOrderItem[];
  subtotal: number;
  shipping: number;
  total: number;
  creator_name: string | null;
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
  meta: p.meta || undefined,
  mediaUrl: p.media_url || undefined,
  // 확장 필드 — 품절/잠금/옵션 UI가 라이브에서도 동작해야 한다(누락 시 서버 422가 최후 방어막이 됨).
  description: p.description || undefined,
  options: p.options?.length ? p.options : undefined,
  stock: p.stock ?? undefined,
  soldOut: p.sold_out || undefined,
  locked: p.locked || undefined,
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
const mapOrder = (o: RawOrder): Order => ({
  id: o.id,
  createdAt: dateLabel(o.created_at),
  status: o.status as OrderStatus,
  items: o.items.map(mapOrderItem),
  subtotal: o.subtotal,
  shipping: o.shipping,
  total: o.total,
  creatorName: o.creator_name ?? undefined,
  refund: o.refund
    ? { status: mapRefundStatus(o.refund.status), reason: o.refund.reason || undefined }
    : undefined,
});
const mapSubscription = (s: RawSubscription): Subscription => ({
  id: s.id,
  creatorId: s.creator_id ?? "",
  creatorName: s.creator_name,
  creatorHandle: s.creator_handle,
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

// --- mock 폴백 데이터 (apiUrl 미설정 시) ------------------------------------
const CREATORS: Creator[] = [
  { id: "c1", name: "별빛 일러스트", handle: "stellar", category: "일러스트", followers: 12400, posts: 320, verified: true, accentColor: "#E14B8A", bio: "별빛이 흐르는 일러스트를 그립니다." },
  { id: "c2", name: "Neon Beats", handle: "neonbeats", category: "뮤직", followers: 8100, accentColor: "#3B82F6" },
  { id: "c3", name: "토끼방송국", handle: "rabbit", category: "버튜버", followers: 23500, accentColor: "#F59E0B" },
  { id: "c4", name: "묘화가", handle: "myo", category: "일러스트", followers: 5200, accentColor: "#10B981" },
  { id: "c5", name: "Studio Lumi", handle: "lumi", category: "굿즈", followers: 3000, accentColor: "#8B5CF6" },
];

const PRODUCTS: Product[] = [
  { id: "p1", creatorId: "c1", creatorName: "별빛 일러스트", type: "goods", title: "아크릴 스탠드", price: 18000, meta: "한정 200개", stock: 143, options: ["A타입 (전신)", "B타입 (반신)"], description: "별빛 일러스트의 대표 캐릭터를 담은 고급 아크릴 스탠드입니다. 두께 3mm 아크릴에 UV 인쇄로 선명한 컬러를 구현했어요." },
  { id: "p2", creatorId: "c1", creatorName: "별빛 일러스트", type: "digital", title: "고해상도 화보집", price: 9900, meta: "다운로드", description: "4K 해상도 일러스트 24종을 담은 디지털 화보집(PDF·PNG). 결제 즉시 다운로드할 수 있습니다." },
  { id: "p3", creatorId: "c1", creatorName: "별빛 일러스트", type: "experience", title: "포토카드 팬사인", price: 30000, meta: "선착순 20", stock: 20, description: "친필 사인이 담긴 포토카드를 받아보세요. 선착순 20명 한정 진행됩니다." },
  { id: "p4", creatorId: "c1", creatorName: "별빛 일러스트", type: "ticket", title: "온라인 팬미팅", price: 25000, meta: "12/24 20:00", description: "12월 24일 저녁 8시, 온라인 팬미팅 입장 티켓입니다. 결제 후 관람 링크가 발송됩니다." },
  { id: "p5", creatorId: "c3", creatorName: "토끼방송국", type: "goods", title: "토끼 아크릴 키링", price: 9000, meta: "재고 12개", stock: 12, options: ["핑크", "블루"], description: "토끼방송국 마스코트 키링. 소량 재고로 준비했어요." },
  { id: "p6", creatorId: "c3", creatorName: "토끼방송국", type: "ticket", title: "버튜버 생일 라이브", price: 15000, meta: "2/14 20:00", description: "생일 기념 스페셜 라이브 입장권. 참여자 전원 디지털 축하 카드 증정." },
  { id: "p7", type: "coupon", title: "웰컴 10% 할인 쿠폰", price: 3000, meta: "30일 유효", description: "첫 구매를 위한 10% 할인 쿠폰. 발급 후 30일간 사용할 수 있습니다." },
  { id: "p8", creatorId: "c4", creatorName: "묘화가", type: "digital", title: "고양이 브러시 팩", price: 6000, meta: "멤버십 전용", locked: true, description: "묘화가 멤버십 구독자에게만 공개되는 디지털 브러시 팩입니다." },
  { id: "p9", creatorId: "c5", creatorName: "Studio Lumi", type: "goods", title: "한정판 피규어", price: 45000, meta: "품절", soldOut: true, stock: 0, description: "Studio Lumi 1주년 기념 한정판 피규어. 현재 품절 상태입니다." },
];

const TIERS: MembershipTier[] = [
  { id: "t1", creatorId: "c1", name: "라이트", price: 4900, period: "월", benefits: ["전용 포스트", "멤버 뱃지"] },
  { id: "t2", creatorId: "c1", name: "스탠다드", price: 9900, period: "월", badge: "인기", featured: true, benefits: ["라이트 혜택 전부", "고해상도 화보", "월간 라이브"] },
  { id: "t3", creatorId: "c1", name: "프리미엄", price: 19900, period: "월", benefits: ["스탠다드 전부", "팬사인 우선", "한정 굿즈 우선"] },
];

const POSTS: Post[] = [
  { id: "po1", creatorId: "c1", creatorName: "별빛 일러스트", creatorMeta: "@stellar · 3시간 전", verified: true, body: "신작 공개! 많은 관심 부탁드려요.", likeCount: 842, commentCount: 2 },
  { id: "po2", creatorId: "c1", creatorName: "별빛 일러스트", creatorMeta: "@stellar · 어제", verified: true, body: "[멤버십 전용] 신작 러프 스케치를 먼저 공개해요.", likeCount: 331, commentCount: 1, locked: true },
  { id: "po3", creatorId: "c3", creatorName: "토끼방송국", creatorMeta: "@rabbit · 2시간 전", body: "오늘 저녁 8시 라이브 켜요! 놀러오세요 🐰", likeCount: 1204, commentCount: 1 },
  { id: "po4", creatorId: "c2", creatorName: "Neon Beats", creatorMeta: "@neonbeats · 5시간 전", body: "새 EP 티저 공개 🎧", likeCount: 512, commentCount: 0 },
  { id: "po5", creatorId: "c4", creatorName: "묘화가", creatorMeta: "@myo · 3일 전", body: "냥이 그림 모음집 작업 중 🐱", likeCount: 210, commentCount: 0 },
  { id: "po6", creatorId: "c5", creatorName: "Studio Lumi", creatorMeta: "@lumi · 1주 전", body: "굿즈 재입고 안내드립니다.", likeCount: 88, commentCount: 0 },
];

const COMMENTS: Comment[] = [
  { id: "cm1", postId: "po1", author: "팬 하나", authorFallback: "팬", body: "응원합니다! 항상 잘 보고 있어요", createdAt: "2시간 전" },
  { id: "cm2", postId: "po1", author: "루미덕후", authorFallback: "루", body: "다음 작품도 기대할게요 🙌", createdAt: "1시간 전" },
  { id: "cm3", postId: "po2", author: "팬 셋", authorFallback: "팬", body: "신청 완료했어요!", createdAt: "20시간 전" },
  { id: "cm4", postId: "po3", author: "토끼팬", authorFallback: "토", body: "기다렸어요!!", createdAt: "1시간 전" },
];

const ORDERS: Order[] = [
  {
    id: "ASN-1024",
    createdAt: "2026-06-28",
    status: "shipping",
    creatorName: "별빛 일러스트",
    items: [
      { productId: "p1", title: "아크릴 스탠드", type: "goods", price: 18000, qty: 1 },
      { productId: "p7", title: "웰컴 10% 할인 쿠폰", type: "coupon", price: 3000, qty: 1 },
    ],
    subtotal: 21000,
    shipping: 3000,
    total: 24000,
    tracking: { carrier: "CJ대한통운", number: "6412-0093-2201" },
  },
  {
    id: "ASN-1019",
    createdAt: "2026-06-20",
    status: "completed",
    creatorName: "별빛 일러스트",
    items: [{ productId: "p2", title: "고해상도 화보집", type: "digital", price: 9900, qty: 1 }],
    subtotal: 9900,
    shipping: 0,
    total: 9900,
  },
  {
    id: "ASN-1003",
    createdAt: "2026-06-10",
    status: "refunding",
    creatorName: "별빛 일러스트",
    items: [{ productId: "p3", title: "포토카드 팬사인", type: "experience", price: 30000, qty: 1 }],
    subtotal: 30000,
    shipping: 0,
    total: 30000,
    refund: { status: "requested", reason: "단순 변심", amount: 30000 },
  },
];

const NOTIFICATIONS: Notification[] = [
  { id: "n1", kind: "like", title: "별빛 일러스트님이 회원님의 댓글을 좋아합니다", time: "3시간 전", group: "today", href: "/post/po1", read: false },
  { id: "n2", kind: "order", title: "주문하신 아크릴 스탠드가 배송을 시작했어요", time: "5시간 전", group: "today", href: "/orders/ASN-1024", read: false },
  { id: "n3", kind: "follow", title: "토끼방송국님이 회원님을 팔로우했습니다", time: "어제", group: "earlier", href: "/creator/rabbit", read: true },
  { id: "n4", kind: "comment", title: "새 댓글이 달렸습니다", time: "2일 전", group: "earlier", href: "/post/po2", read: true },
  { id: "n5", kind: "system", title: "멤버십 다음 결제 예정일이 3일 남았어요", time: "3일 전", group: "earlier", href: "/mypage/subscriptions", read: true },
];

const SUBSCRIPTIONS: Subscription[] = [
  { id: "s1", creatorId: "c1", creatorName: "별빛 일러스트", creatorHandle: "stellar", tierName: "스탠다드", price: 9900, period: "월", nextBillingDate: "2026-07-15", status: "active" },
  { id: "s2", creatorId: "c3", creatorName: "토끼방송국", creatorHandle: "rabbit", tierName: "라이트", price: 4900, period: "월", nextBillingDate: "2026-07-22", status: "active" },
];

// --- 도메인 함수 (apiUrl 설정 시 실 B2 API, 아니면 mock 폴백) ----------------
export async function getCreators(): Promise<Creator[]> {
  if (USE_API) return (await apiFetch<Paginated<RawCreator>>("/creators")).items.map(mapCreator);
  return CREATORS;
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
  return CREATORS.find((c) => c.handle === handle);
}
export async function getProducts(creatorId?: string): Promise<Product[]> {
  if (USE_API) {
    const q = creatorId ? `?creator_id=${encodeURIComponent(creatorId)}` : "";
    return (await apiFetch<Paginated<RawProduct>>(`/products${q}`)).items.map(mapProduct);
  }
  return creatorId ? PRODUCTS.filter((p) => p.creatorId === creatorId) : PRODUCTS;
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
/** 피드 — B2 `/feed` 소비(익명=최신 전체). B3 개인화(팔로잉) 피드의 배선 지점. */
export async function getFeed(): Promise<Post[]> {
  if (USE_API) return (await apiFetch<Paginated<RawPost>>("/feed")).items.map(mapPost);
  return POSTS;
}
/** 검색 — B2 `/search?q=` 소비. mock 폴백은 서버 의미론(name/handle·title 부분일치, 10건)을 미러. */
export async function getSearch(q: string): Promise<SearchResult> {
  const term = q.trim();
  if (!term) return { creators: [], products: [] };
  if (USE_API) {
    const raw = await apiFetch<RawSearch>(`/search?q=${encodeURIComponent(term)}`);
    return { creators: raw.creators.map(mapCreator), products: raw.products.map(mapProductBrief) };
  }
  const t = term.toLowerCase();
  return {
    // name/handle 외 category 부분일치도 포함 → 카테고리 아이콘 행(디스커버리)에서 착지 보강.
    creators: CREATORS.filter(
      (c) =>
        c.name.toLowerCase().includes(t) ||
        c.handle.toLowerCase().includes(t) ||
        (c.category?.toLowerCase().includes(t) ?? false),
    ).slice(0, 10),
    products: PRODUCTS.filter((p) => p.title.toLowerCase().includes(t)).slice(0, 10),
  };
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
/** 주문 생성(mock 결제 확정 — 실 PG·금액이동 없음) → 201 Order. */
export async function apiCreateOrder(input: { productId: string; qty: number; option?: string }): Promise<Order> {
  const raw = await apiFetch<RawOrder>("/orders", {
    method: "POST",
    body: JSON.stringify({ product_id: input.productId, qty: input.qty, option: input.option }),
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
/** 포스트 발행(크리에이터 오너만 — 403 시 안내) → 201 Post. */
export async function apiPublishPost(input: { body: string; mediaUrl?: string }): Promise<Post> {
  const raw = await apiFetch<RawPost>("/posts", {
    method: "POST",
    body: JSON.stringify({ body: input.body, media_url: input.mediaUrl }),
  });
  return mapPost(raw);
}
