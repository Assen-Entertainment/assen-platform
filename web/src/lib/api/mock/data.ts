/**
 * mock 폴백 데이터 — `NEXT_PUBLIC_API_URL` 미설정(빌드/CI/오프라인·테스트) 시에만 소비된다.
 *
 * ★번들 격리(R6-W2C): 이 모듈은 lib/api/index.ts의 USE_API=false 폴백 경로에서만 참조된다.
 * 라이브 빌드(NEXT_PUBLIC_API_URL 설정)에선 index.ts의 `USE_API`가 빌드타임 상수 `true`로 접혀
 * 폴백 분기가 DCE되고, 여기의 mock 데이터는 트리셰이킹으로 클라이언트 번들에서 제거된다
 * (실증: 라이브 빌드 후 `.next/static`에서 "별빛 일러스트"·"ASN-1024" 등 grep 0건).
 * 따라서 이 파일은 **순수 데이터/순수 함수만** 유지한다(모듈 로드 부수효과 금지 — 트리셰이킹 보존).
 *
 * 값은 기존 index.ts in-file mock과 1:1 동일(회귀 0) — 파일 이동만 수행했다.
 */
import type {
  Comment,
  Creator,
  MembershipTier,
  Notification,
  Order,
  Post,
  Product,
  SavedPaymentMethod,
  StudioStats,
  Subscription,
} from "../types";
// STUDIO_STATS의 상품 카운트 파생용 — 스튜디오 카탈로그 mock(정본은 studio-mock).
import { STUDIO_PRODUCTS } from "@/lib/studio-mock";

export const CREATORS: Creator[] = [
  { id: "c1", name: "별빛 일러스트", handle: "stellar", category: "일러스트", followers: 12400, posts: 320, verified: true, accentColor: "#E14B8A", bio: "별빛이 흐르는 일러스트를 그립니다." },
  { id: "c2", name: "Neon Beats", handle: "neonbeats", category: "뮤직", followers: 8100, accentColor: "#3B82F6" },
  { id: "c3", name: "토끼방송국", handle: "rabbit", category: "버튜버", followers: 23500, accentColor: "#F59E0B" },
  { id: "c4", name: "묘화가", handle: "myo", category: "일러스트", followers: 5200, accentColor: "#10B981" },
  // 굿즈는 상품유형이라 크리에이터 카테고리(정본 CREATOR_CATEGORIES)에서 제외 — '일러스트'로 매핑(서버 seed_demo와 일치).
  { id: "c5", name: "Studio Lumi", handle: "lumi", category: "일러스트", followers: 3000, accentColor: "#8B5CF6" },
];

export const PRODUCTS: Product[] = [
  { id: "p1", creatorId: "c1", creatorName: "별빛 일러스트", creatorHandle: "stellar", type: "goods", title: "아크릴 스탠드", price: 18000, meta: "한정 200개", stock: 143, options: ["A타입 (전신)", "B타입 (반신)"], description: "별빛 일러스트의 대표 캐릭터를 담은 고급 아크릴 스탠드입니다. 두께 3mm 아크릴에 UV 인쇄로 선명한 컬러를 구현했어요." },
  { id: "p2", creatorId: "c1", creatorName: "별빛 일러스트", creatorHandle: "stellar", type: "digital", title: "고해상도 화보집", price: 9900, meta: "다운로드", description: "4K 해상도 일러스트 24종을 담은 디지털 화보집(PDF·PNG). 결제 즉시 다운로드할 수 있습니다." },
  { id: "p3", creatorId: "c1", creatorName: "별빛 일러스트", creatorHandle: "stellar", type: "experience", title: "포토카드 팬사인", price: 30000, meta: "선착순 20", stock: 20, description: "친필 사인이 담긴 포토카드를 받아보세요. 선착순 20명 한정 진행됩니다." },
  { id: "p4", creatorId: "c1", creatorName: "별빛 일러스트", creatorHandle: "stellar", type: "ticket", title: "온라인 팬미팅", price: 25000, meta: "12/24 20:00", description: "12월 24일 저녁 8시, 온라인 팬미팅 입장 티켓입니다. 결제 후 관람 링크가 발송됩니다." },
  { id: "p5", creatorId: "c3", creatorName: "토끼방송국", creatorHandle: "rabbit", type: "goods", title: "토끼 아크릴 키링", price: 9000, meta: "재고 12개", stock: 12, options: ["핑크", "블루"], description: "토끼방송국 마스코트 키링. 소량 재고로 준비했어요." },
  { id: "p6", creatorId: "c3", creatorName: "토끼방송국", creatorHandle: "rabbit", type: "ticket", title: "버튜버 생일 라이브", price: 15000, meta: "2/14 20:00", description: "생일 기념 스페셜 라이브 입장권. 참여자 전원 디지털 축하 카드 증정." },
  { id: "p7", type: "coupon", title: "웰컴 10% 할인 쿠폰", price: 3000, meta: "30일 유효", description: "첫 구매를 위한 10% 할인 쿠폰. 발급 후 30일간 사용할 수 있습니다." },
  { id: "p8", creatorId: "c4", creatorName: "묘화가", creatorHandle: "myo", type: "digital", title: "고양이 브러시 팩", price: 6000, meta: "멤버십 전용", locked: true, description: "묘화가 멤버십 구독자에게만 공개되는 디지털 브러시 팩입니다." },
  { id: "p9", creatorId: "c5", creatorName: "Studio Lumi", creatorHandle: "lumi", type: "goods", title: "한정판 피규어", price: 45000, meta: "품절", soldOut: true, stock: 0, description: "Studio Lumi 1주년 기념 한정판 피규어. 현재 품절 상태입니다." },
];

export const TIERS: MembershipTier[] = [
  { id: "t1", creatorId: "c1", name: "라이트", price: 4900, period: "월", benefits: ["전용 포스트", "멤버 뱃지"] },
  { id: "t2", creatorId: "c1", name: "스탠다드", price: 9900, period: "월", badge: "인기", featured: true, benefits: ["라이트 혜택 전부", "고해상도 화보", "월간 라이브"] },
  { id: "t3", creatorId: "c1", name: "프리미엄", price: 19900, period: "월", benefits: ["스탠다드 전부", "팬사인 우선", "한정 굿즈 우선"] },
];

export const POSTS: Post[] = [
  { id: "po1", creatorId: "c1", creatorName: "별빛 일러스트", creatorHandle: "stellar", creatorMeta: "@stellar · 3시간 전", verified: true, body: "신작 공개! 많은 관심 부탁드려요.", likeCount: 842, commentCount: 2 },
  { id: "po2", creatorId: "c1", creatorName: "별빛 일러스트", creatorHandle: "stellar", creatorMeta: "@stellar · 어제", verified: true, body: "[멤버십 전용] 신작 러프 스케치를 먼저 공개해요.", likeCount: 331, commentCount: 1, locked: true },
  { id: "po3", creatorId: "c3", creatorName: "토끼방송국", creatorHandle: "rabbit", creatorMeta: "@rabbit · 2시간 전", body: "오늘 저녁 8시 라이브 켜요! 놀러오세요 🐰", likeCount: 1204, commentCount: 1 },
  { id: "po4", creatorId: "c2", creatorName: "Neon Beats", creatorHandle: "neonbeats", creatorMeta: "@neonbeats · 5시간 전", body: "새 EP 티저 공개 🎧", likeCount: 512, commentCount: 0 },
  { id: "po5", creatorId: "c4", creatorName: "묘화가", creatorHandle: "myo", creatorMeta: "@myo · 3일 전", body: "냥이 그림 모음집 작업 중 🐱", likeCount: 210, commentCount: 0 },
  { id: "po6", creatorId: "c5", creatorName: "Studio Lumi", creatorHandle: "lumi", creatorMeta: "@lumi · 1주 전", body: "굿즈 재입고 안내드립니다.", likeCount: 88, commentCount: 0 },
];

export const COMMENTS: Comment[] = [
  { id: "cm1", postId: "po1", author: "팬 하나", authorFallback: "팬", body: "응원합니다! 항상 잘 보고 있어요", createdAt: "2시간 전" },
  { id: "cm2", postId: "po1", author: "루미덕후", authorFallback: "루", body: "다음 작품도 기대할게요 🙌", createdAt: "1시간 전" },
  { id: "cm3", postId: "po2", author: "팬 셋", authorFallback: "팬", body: "신청 완료했어요!", createdAt: "20시간 전" },
  { id: "cm4", postId: "po3", author: "토끼팬", authorFallback: "토", body: "기다렸어요!!", createdAt: "1시간 전" },
];

export const ORDERS: Order[] = [
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
    // 배송비=0 고정(정책 게이트) — 날조 금액 금지. total = subtotal + shipping.
    shipping: 0,
    total: 21000,
    shippingAddress: {
      recipientName: "데모 팬",
      recipientPhone: "010-0000-0002",
      postalCode: "04524",
      address1: "서울 중구 세종대로 110",
      address2: "1203호",
    },
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

export const NOTIFICATIONS: Notification[] = [
  { id: "n1", kind: "like", title: "별빛 일러스트님이 회원님의 댓글을 좋아합니다", time: "3시간 전", group: "today", href: "/post/po1", read: false },
  { id: "n2", kind: "order", title: "주문하신 아크릴 스탠드가 배송을 시작했어요", time: "5시간 전", group: "today", href: "/orders/ASN-1024", read: false },
  { id: "n3", kind: "follow", title: "토끼방송국님이 회원님을 팔로우했습니다", time: "어제", group: "earlier", href: "/creator/rabbit", read: true },
  { id: "n4", kind: "comment", title: "새 댓글이 달렸습니다", time: "2일 전", group: "earlier", href: "/post/po2", read: true },
  { id: "n5", kind: "system", title: "멤버십 다음 결제 예정일이 3일 남았어요", time: "3일 전", group: "earlier", href: "/mypage/subscriptions", read: true },
];

export const SUBSCRIPTIONS: Subscription[] = [
  { id: "s1", creatorId: "c1", creatorName: "별빛 일러스트", creatorHandle: "stellar", tierId: "t2", tierName: "스탠다드", price: 9900, period: "월", nextBillingDate: "2026-07-15", status: "active" },
  { id: "s2", creatorId: "c3", creatorName: "토끼방송국", creatorHandle: "rabbit", tierName: "라이트", price: 4900, period: "월", nextBillingDate: "2026-07-22", status: "active" },
];

// 결제수단 mock 폴백(표시용 — 실 카드정보 아님). last4만 노출.
export const PAYMENT_METHODS: SavedPaymentMethod[] = [
  { id: "m1", brand: "신한카드", last4: "4321", isPrimary: true, createdAt: "2026-06-01T00:00:00Z" },
  { id: "m2", brand: "카카오페이", last4: "8890", isPrimary: false, createdAt: "2026-06-10T00:00:00Z" },
];

/**
 * 스튜디오 대시보드 실 카운트 mock 폴백 — 기존 mock 대시보드 수치와 일관(회귀 0).
 * followers 12,400은 기존 하드코딩 대시보드 카드 및 데모 오너(별빛 일러스트) 값과 일치,
 * products/productsSelling은 STUDIO_PRODUCTS(스튜디오 상품 mock)에서 파생, subscribers 872는
 * 애널리틱스 시계열 최근월(6월) 활성 구독자와 일치, orders 124는 최근 항목 "판매 124"와 일치.
 * ※금액 필드는 없다(정산 게이트) — mock도 금액을 날조하지 않는다.
 */
export const STUDIO_STATS: StudioStats = {
  followers: 12400,
  posts: 320,
  products: STUDIO_PRODUCTS.length,
  productsSelling: STUDIO_PRODUCTS.filter((p) => p.status === "selling").length,
  orders: 124,
  subscribers: 872,
};

// mock 차단 상태(USE_API=false 로컬 시뮬 — 실 경로는 서버가 권위). getBlocks/getCreator 코히어런스.
export const MOCK_BLOCKED = new Set<string>();
/** mock 차단/해제 반영(설정 목록·프로필 blocked 일관성). 뮤테이션 훅의 mock 분기에서 호출. */
export function mockSetBlocked(creatorId: string, blocked: boolean): void {
  if (blocked) MOCK_BLOCKED.add(creatorId);
  else MOCK_BLOCKED.delete(creatorId);
}
