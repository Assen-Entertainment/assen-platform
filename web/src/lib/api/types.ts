import type { MonetizableItemType } from "@/components/ui";

export interface Creator {
  id: string;
  name: string;
  handle: string;
  bio?: string;
  /** 크리에이터 시그니처 색(hex) — creatorAccent 주입. */
  accentColor?: string;
  avatarUrl?: string;
  coverUrl?: string;
  followers: number;
  posts?: number;
  verified?: boolean;
  category?: string;
  following?: boolean;
}

export interface Post {
  id: string;
  creatorId: string;
  creatorName: string;
  creatorMeta?: string;
  verified?: boolean;
  body?: string;
  mediaUrl?: string;
  likeCount: number;
  commentCount: number;
  liked?: boolean;
  /** 멤버십 전용 잠금 포스트(LockedOverlay 노출·루브릭 #16). mock 전용(실 API 시 undefined). */
  locked?: boolean;
}

export interface Comment {
  id: string;
  postId: string;
  author: string;
  authorFallback?: string;
  body: string;
  /** 상대 시각 라벨(목업). 실 API 시 ISO → 포맷. */
  createdAt: string;
}

export interface Product {
  id: string;
  /** 소유 크리에이터(스토어 스코프). 전역 카탈로그 항목은 미지정. */
  creatorId?: string;
  type: MonetizableItemType;
  title: string;
  price: number;
  meta?: string;
  mediaUrl?: string;
  /** 크리에이터 표시명(상세/체크아웃 요약). mock 편의 필드. */
  creatorName?: string;
  // --- 이하 W2 상세용 확장 필드 (openapi.json 미제공 → mock 전용, 실 API 시 undefined) ---
  /** 상세 설명 문단(상품 상세). */
  description?: string;
  /** 선택 옵션(OptionSwatch). 예: ["A타입", "B타입"]. */
  options?: string[];
  /** 재고 수량. 0 이하 또는 soldOut=true 면 품절 처리. */
  stock?: number;
  /** 품절 플래그(mock). */
  soldOut?: boolean;
  /** 잠금 상품(멤버십/구독 전용) — LockedOverlay 노출. */
  locked?: boolean;
}

export interface MembershipTier {
  id: string;
  /** 소유 크리에이터. 전역 목록은 미지정. */
  creatorId?: string;
  name: string;
  price: number;
  period: string;
  benefits: string[];
  badge?: string;
  featured?: boolean;
}

/** 커서 페이지 응답 — B2 wire 계약(snake_case). 마지막 페이지에서 next_cursor=null. */
export interface Paginated<T> {
  items: T[];
  next_cursor?: string | null;
}

/** /search 결과 (creators + products). */
export interface SearchResult {
  creators: Creator[];
  products: Product[];
}

// --- 커머스 상태/주문 (W2, openapi.json 미제공 → mock 전용) ------------------

/** 주문 상태 — StatusChip 매핑. paid/shipping/completed=진행·완료, cancelled/refunding/refunded=취소·환불. */
export type OrderStatus =
  | "paid"
  | "shipping"
  | "completed"
  | "cancelled"
  | "refunding"
  | "refunded";

/** 환불 진행 상태(mock). */
export type RefundStatus = "requested" | "approved" | "rejected";

export interface OrderItem {
  productId: string;
  title: string;
  type: MonetizableItemType;
  price: number;
  qty: number;
}

export interface Order {
  id: string;
  /** 표시용 주문 일자(YYYY-MM-DD). */
  createdAt: string;
  status: OrderStatus;
  items: OrderItem[];
  subtotal: number;
  shipping: number;
  total: number;
  creatorName?: string;
  /** 배송 추적(placeholder) — 물리 굿즈 주문에만. */
  tracking?: { carrier: string; number: string };
  /** 환불 신청 상태(있으면 환불 흐름 진행 중). */
  refund?: { status: RefundStatus; reason?: string; amount?: number };
}

/** 알림 종류 — 아이콘/라우트 파생. */
export type NotificationKind = "like" | "comment" | "follow" | "order" | "system";

export interface Notification {
  id: string;
  kind: NotificationKind;
  title: string;
  /** 상대 시각 라벨(목업). */
  time: string;
  /** 그룹핑 — 오늘 / 이전. */
  group: "today" | "earlier";
  /** 클릭 시 이동 경로. */
  href?: string;
  read?: boolean;
}

/** 구독(멤버십) — 마이페이지 구독 관리. */
export interface Subscription {
  id: string;
  creatorId: string;
  creatorName: string;
  creatorHandle: string;
  tierName: string;
  price: number;
  period: string;
  /** 다음 결제일(YYYY-MM-DD, mock). */
  nextBillingDate: string;
  status: "active" | "cancelled";
}
