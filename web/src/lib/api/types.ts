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
  /** 19+ 성인 등급(서버 PostOut.is_adult). 미인증 뷰어에겐 서버가 이미 숨기나 UI도 방어적으로 블러. */
  isAdult?: boolean;
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
  /** 크리에이터 표시명(상세/체크아웃 요약). 서버 ProductOut(creator_name) 계약. */
  creatorName?: string;
  // --- 이하 상세용 확장 필드 — 서버 ProductOut(B4) 계약. 값 없으면 undefined. ---
  /** 상세 설명 문단(상품 상세). */
  description?: string;
  /** 선택 옵션(OptionSwatch). 예: ["A타입", "B타입"]. */
  options?: string[];
  /** 재고 수량. 0 이하 또는 soldOut=true 면 품절 처리. */
  stock?: number;
  /** 품절 플래그. */
  soldOut?: boolean;
  /** 잠금 상품(멤버십/구독 전용) — LockedOverlay 노출. */
  locked?: boolean;
  /** 19+ 성인 등급(서버 ProductOut.is_adult). 게이팅 UI 방어용. */
  isAdult?: boolean;
  /** 판매 상태 — 오너 스코프(StudioProductOut.status). 공개 카탈로그 응답엔 없어 있을 때만 채워짐. */
  status?: string;
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

// --- 커머스 상태/주문 — 서버 wire 계약(B4). OrderStatus/RefundStatus는 서버 상태 매핑. ---

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
  /** 선택한 옵션(예: "A타입") — 있을 때만 표기. 서버 OrderItemOut(option) 계약. */
  option?: string;
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

/**
 * 저장된 결제수단 — 서버 SavedPaymentMethod 계약.
 * ※PCI(R4): brand+last4만 보관 — 실 카드번호(PAN)/CVC는 저장·전송하지 않는다.
 */
export interface SavedPaymentMethod {
  id: string;
  brand: string;
  last4: string;
  isPrimary: boolean;
  /** 등록 시각(ISO). */
  createdAt: string;
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
  /** 다음 결제일(YYYY-MM-DD). */
  nextBillingDate: string;
  status: "active" | "cancelled";
  /** 해지 예정 — 서버 계약: status=active 유지 + cancel_scheduled=true(말일 해지). */
  cancelScheduled?: boolean;
}
