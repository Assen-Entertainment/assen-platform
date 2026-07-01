/**
 * Assen 도메인 API.
 * ⚠️ 현재 백엔드 연동 전이라 mock 반환. 실 API 준비 시 각 함수 본문을 `apiFetch`로 교체
 *   (시그니처/타입은 유지 → 화면 코드 무변경). client.ts·types.ts 참조.
 */
import type { Creator, Post, Product, MembershipTier, Comment } from "./types";

export * from "./types";
export { apiFetch, ApiError } from "./client";

const CREATORS: Creator[] = [
  { id: "c1", name: "별빛 일러스트", handle: "stellar", category: "일러스트", followers: 12400, posts: 320, verified: true, accentColor: "#E14B8A", bio: "별빛이 흐르는 일러스트를 그립니다." },
  { id: "c2", name: "Neon Beats", handle: "neonbeats", category: "뮤직", followers: 8100, accentColor: "#3B82F6" },
  { id: "c3", name: "토끼방송국", handle: "rabbit", category: "버튜버", followers: 23500, accentColor: "#F59E0B" },
  { id: "c4", name: "묘화가", handle: "myo", category: "일러스트", followers: 5200, accentColor: "#10B981" },
  { id: "c5", name: "Studio Lumi", handle: "lumi", category: "굿즈", followers: 3000, accentColor: "#8B5CF6" },
];

const PRODUCTS: Product[] = [
  { id: "p1", type: "goods", title: "아크릴 스탠드", price: 18000, meta: "한정 200개" },
  { id: "p2", type: "digital", title: "고해상도 화보집", price: 9900, meta: "다운로드" },
  { id: "p3", type: "experience", title: "포토카드 팬사인", price: 30000, meta: "선착순 20" },
  { id: "p4", type: "ticket", title: "온라인 팬미팅", price: 25000, meta: "12/24 20:00" },
];

const TIERS: MembershipTier[] = [
  { id: "t1", name: "라이트", price: 4900, period: "월", benefits: ["전용 포스트", "멤버 뱃지"] },
  { id: "t2", name: "스탠다드", price: 9900, period: "월", badge: "인기", featured: true, benefits: ["라이트 혜택 전부", "고해상도 화보", "월간 라이브"] },
  { id: "t3", name: "프리미엄", price: 19900, period: "월", benefits: ["스탠다드 전부", "팬사인 우선", "한정 굿즈 우선"] },
];

export async function getCreators(): Promise<Creator[]> {
  return CREATORS;
}
export async function getCreator(handle: string): Promise<Creator | undefined> {
  return CREATORS.find((c) => c.handle === handle);
}
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

export async function getProducts(): Promise<Product[]> {
  return PRODUCTS;
}
export async function getMembershipTiers(_creatorId?: string): Promise<MembershipTier[]> {
  return TIERS;
}
/** creatorId 지정 시 해당 크리에이터 포스트, 미지정 시 전체(피드). */
export async function getPosts(creatorId?: string): Promise<Post[]> {
  return creatorId ? POSTS.filter((p) => p.creatorId === creatorId) : POSTS;
}
export async function getPost(id: string): Promise<Post | undefined> {
  return POSTS.find((p) => p.id === id);
}
export async function getComments(postId: string): Promise<Comment[]> {
  return COMMENTS.filter((c) => c.postId === postId);
}
