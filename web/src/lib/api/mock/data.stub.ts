/**
 * mock 데이터 스텁(R6-W2C 번들 격리) — 라이브 빌드(NEXT_PUBLIC_API_URL 설정) 전용 웹팩 치환 타깃.
 *
 * ★배경: index.ts의 `USE_API` 분기는 빌드타임 상수이지만, 측정 결과(라이브 빌드 grep) SWC 미니파이어가
 * async/await·try-catch를 낀 각 함수의 mock 폴백 `return`문까지는 사병(dead-code) 제거하지 못했다
 * (실측: 스텁 적용 전 라이브 빌드에도 "별빛 일러스트" 등 mock 문자열이 그대로 잔존). 따라서 미니파이어
 * 최적화에 기대는 대신, next.config.mjs의 NormalModuleReplacementPlugin이 라이브 빌드에서
 * `./mock/data`(실 데이터)를 이 스텁으로 **물리 치환**해 확정적으로 제거한다.
 *
 * ★안전성: USE_API=true 런타임 경로는 index.ts가 이 값들을 절대 읽지 않는다(if(USE_API) 분기가
 * 먼저 return/throw하므로 폴백 코드는 도달 불가) — 따라서 빈 값으로 대체해도 의미론적 회귀가 없다.
 * dev(mock 빌드)·vitest는 이 파일을 참조하지 않는다(웹팩 프로덕션 빌드 전용 치환 — 실 데이터 정본은 ./data).
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

export const CREATORS: Creator[] = [];
export const PRODUCTS: Product[] = [];
export const TIERS: MembershipTier[] = [];
export const POSTS: Post[] = [];
export const COMMENTS: Comment[] = [];
export const ORDERS: Order[] = [];
export const NOTIFICATIONS: Notification[] = [];
export const SUBSCRIPTIONS: Subscription[] = [];
export const PAYMENT_METHODS: SavedPaymentMethod[] = [];
export const STUDIO_STATS: StudioStats = {
  followers: 0,
  posts: 0,
  products: 0,
  productsSelling: 0,
  orders: 0,
  subscribers: 0,
};
export const MOCK_BLOCKED = new Set<string>();
export function mockSetBlocked(_creatorId: string, _blocked: boolean): void {
  /* 라이브 빌드 전용 스텁 — USE_API=true 경로는 이 함수를 호출하지 않는다(no-op). */
}
