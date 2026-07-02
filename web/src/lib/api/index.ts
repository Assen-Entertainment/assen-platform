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
import type { Comment, Creator, MembershipTier, Paginated, Post, Product, SearchResult } from "./types";

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
  type: string;
  title: string;
  price: number;
  meta: string;
  media_url: string;
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
  type: p.type as Product["type"],
  title: p.title,
  price: p.price,
  meta: p.meta || undefined,
  mediaUrl: p.media_url || undefined,
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

// --- mock 폴백 데이터 (apiUrl 미설정 시) ------------------------------------
const CREATORS: Creator[] = [
  { id: "c1", name: "별빛 일러스트", handle: "stellar", category: "일러스트", followers: 12400, posts: 320, verified: true, accentColor: "#E14B8A", bio: "별빛이 흐르는 일러스트를 그립니다." },
  { id: "c2", name: "Neon Beats", handle: "neonbeats", category: "뮤직", followers: 8100, accentColor: "#3B82F6" },
  { id: "c3", name: "토끼방송국", handle: "rabbit", category: "버튜버", followers: 23500, accentColor: "#F59E0B" },
  { id: "c4", name: "묘화가", handle: "myo", category: "일러스트", followers: 5200, accentColor: "#10B981" },
  { id: "c5", name: "Studio Lumi", handle: "lumi", category: "굿즈", followers: 3000, accentColor: "#8B5CF6" },
];

const PRODUCTS: Product[] = [
  { id: "p1", creatorId: "c1", type: "goods", title: "아크릴 스탠드", price: 18000, meta: "한정 200개" },
  { id: "p2", creatorId: "c1", type: "digital", title: "고해상도 화보집", price: 9900, meta: "다운로드" },
  { id: "p3", creatorId: "c1", type: "experience", title: "포토카드 팬사인", price: 30000, meta: "선착순 20" },
  { id: "p4", creatorId: "c1", type: "ticket", title: "온라인 팬미팅", price: 25000, meta: "12/24 20:00" },
];

const TIERS: MembershipTier[] = [
  { id: "t1", creatorId: "c1", name: "라이트", price: 4900, period: "월", benefits: ["전용 포스트", "멤버 뱃지"] },
  { id: "t2", creatorId: "c1", name: "스탠다드", price: 9900, period: "월", badge: "인기", featured: true, benefits: ["라이트 혜택 전부", "고해상도 화보", "월간 라이브"] },
  { id: "t3", creatorId: "c1", name: "프리미엄", price: 19900, period: "월", benefits: ["스탠다드 전부", "팬사인 우선", "한정 굿즈 우선"] },
];

const POSTS: Post[] = [
  { id: "po1", creatorId: "c1", creatorName: "별빛 일러스트", creatorMeta: "@stellar · 3시간 전", verified: true, body: "신작 공개! 많은 관심 부탁드려요.", likeCount: 842, commentCount: 2 },
  { id: "po2", creatorId: "c1", creatorName: "별빛 일러스트", creatorMeta: "@stellar · 어제", verified: true, body: "다음 주 팬미팅 신청 받아요.", likeCount: 331, commentCount: 1 },
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
    creators: CREATORS.filter(
      (c) => c.name.toLowerCase().includes(t) || c.handle.toLowerCase().includes(t),
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
