// 스튜디오 mock 데이터 — Wave 3 소유. 실 API(B2)·정산·결제 미연동.
// ※수익/수수료/원천징수/정산 수치는 전부 placeholder — 대표·재무·법무 게이트(단독 확정 금지).
//   여기 값은 UI 종단 데모용이며 실제 정산 규정이 아니다.
import type { MonetizableItemType } from "@/components/ui";

/** 공개 범위 — 포스트 작성기 Select 매핑. */
export type PostVisibility = "public" | "members" | "tier";

export const VISIBILITY_OPTIONS: { value: PostVisibility; label: string; hint: string }[] = [
  { value: "public", label: "전체 공개", hint: "누구나 볼 수 있어요." },
  { value: "members", label: "멤버십 전용", hint: "구독 중인 멤버에게만 공개돼요." },
  { value: "tier", label: "특정 티어 이상", hint: "선택한 티어 이상 멤버에게만 공개돼요." },
];

/** 상품 판매 상태. */
export type ProductStatus = "selling" | "soldout" | "draft" | "hidden";

export const PRODUCT_STATUS_META: Record<ProductStatus, { label: string; variant: "success" | "neutral" | "warning" | "error" }> = {
  selling: { label: "판매중", variant: "success" },
  soldout: { label: "품절", variant: "error" },
  draft: { label: "임시저장", variant: "neutral" },
  hidden: { label: "숨김", variant: "warning" },
};

export interface StudioProduct {
  id: string;
  type: MonetizableItemType;
  title: string;
  price: number;
  status: ProductStatus;
  /** 누적 판매수(비취소 주문 기준, ASS-264). 카운트만 — 수익 금액 아님. */
  sold?: number;
  /** 재고(디지털/무제한형은 null). */
  stock: number | null;
  updatedAt: string;
  /** 가격 종류(서버 pricing_kind, 기본 "paid") — "free"면 무료 상품(가격 0 강제). */
  pricingKind?: "paid" | "free";
}

// sold/subscribers는 실 API 경로(ASS-264 집계)와 패리티를 위해 mock에도 합리적인 값을 채운다.
// 어디까지나 UI 데모용 수치이며 수익/정산 금액은 아니다(카운트만).
export const STUDIO_PRODUCTS: StudioProduct[] = [
  { id: "p1", type: "goods", title: "아크릴 스탠드 (블루)", price: 18000, status: "selling", sold: 124, stock: 76, updatedAt: "2일 전" },
  { id: "p2", type: "digital", title: "고해상도 일러스트 팩 vol.3", price: 9000, status: "selling", sold: 58, stock: null, updatedAt: "5일 전" },
  { id: "p3", type: "ticket", title: "온라인 팬미팅 티켓", price: 25000, status: "soldout", sold: 40, stock: 0, updatedAt: "1주 전" },
  { id: "p4", type: "experience", title: "1:1 화상 스케치 클래스", price: 55000, status: "selling", sold: 8, stock: 8, updatedAt: "3일 전" },
  { id: "p5", type: "coupon", title: "굿즈 10% 할인 쿠폰", price: 0, status: "hidden", sold: 0, stock: null, updatedAt: "2주 전" },
  { id: "p6", type: "goods", title: "홀로그램 스티커 세트", price: 6000, status: "draft", sold: 0, stock: 300, updatedAt: "방금" },
];

export interface StudioTier {
  id: string;
  name: string;
  price: number;
  benefits: string[];
  /** 활성(status=active) 구독자수(ASS-264). 카운트만 — 수익 금액 아님. */
  subscribers?: number;
  active: boolean;
  /** 가격 종류(서버 pricing_kind, 기본 "paid") — "free"면 무료 멤버십(가격 0 강제). */
  pricingKind?: "paid" | "free";
}

// subscribers도 실 API 경로와 패리티를 위해 mock에 합리적인 값을 채운다(카운트만, 수익 아님).
export const STUDIO_TIERS: StudioTier[] = [
  {
    id: "t1",
    name: "베이직",
    price: 5000,
    benefits: ["멤버 전용 포스트", "월 1회 라이브"],
    subscribers: 142,
    active: true,
  },
  {
    id: "t2",
    name: "스탠다드",
    price: 12000,
    benefits: ["베이직 혜택 포함", "고해상도 원본", "월 2회 라이브", "굿즈 5% 할인"],
    subscribers: 286,
    active: true,
  },
  {
    id: "t3",
    name: "프리미엄",
    price: 30000,
    benefits: ["스탠다드 혜택 포함", "1:1 팬레터 답장", "한정 굿즈 우선권", "이름 크레딧"],
    subscribers: 37,
    active: true,
  },
];

// ※정산/수익 재무 mock(SETTLEMENT_ROWS·ANALYTICS_SERIES 등)은 studio-mock-finance로 분리했다
//   (ASS-289 #5) — 라이브 빌드에서 날조 금액이 번들에 실리지 않도록 mock 데모 경로 전용 모듈로 격리.

export interface StudioRecentItem {
  title: string;
  meta: string;
  href: string;
}

export const STUDIO_RECENT: StudioRecentItem[] = [
  { title: "신작 일러스트 공개", meta: "포스트 · 좋아요 842", href: "/studio/posts" },
  { title: "아크릴 스탠드 (블루)", meta: "상품 · 판매 124", href: "/studio/products" },
  { title: "스탠다드 멤버십", meta: "멤버십 · 구독 286", href: "/studio/membership" },
];

// 원화 포맷 — lib/checkout의 won을 정본으로 재노출(중복 정의 제거, 기존 소비처 무수정).
export { won } from "@/lib/checkout";

/** 포스트 작성기 초안. */
export interface ComposerDraft {
  title: string;
  body: string;
  visibility: PostVisibility;
  adult: boolean;
}

export interface ComposerValidation {
  valid: boolean;
  errors: Partial<Record<"title" | "body", string>>;
}

/**
 * 작성기 검증 — 제목·본문 필수, 제목 60자 이내.
 * 발행 버튼 활성/에러 표기에 사용(순수 함수 → 단위 테스트 대상).
 */
export function validateComposerDraft(draft: ComposerDraft): ComposerValidation {
  const errors: ComposerValidation["errors"] = {};
  const title = draft.title.trim();
  const body = draft.body.trim();
  if (!title) errors.title = "제목을 입력해 주세요.";
  else if (title.length > 60) errors.title = "제목은 60자 이내로 입력해 주세요.";
  if (!body) errors.body = "본문을 입력해 주세요.";
  return { valid: Object.keys(errors).length === 0, errors };
}
