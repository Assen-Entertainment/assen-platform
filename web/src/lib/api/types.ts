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
  /** 팬 개인 차단 여부(서버 CreatorOut.blocked) — 단건 조회에서 인증 팬이 차단 시 true. */
  blocked?: boolean;
}

/** 내가 차단한 크리에이터 1건(설정 차단 목록 — 서버 BlockedCreatorOut). */
export interface BlockedCreator {
  creatorId: string;
  name: string;
  handle: string;
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
  /**
   * 소유 크리에이터 핸들 — 스토어/PDP에서 크리에이터 프로필(/creator/[handle]) 링크용.
   * 서버 ProductOut엔 아직 없어(creator_name만) 옵셔널 — 없으면 링크 없이 이름만 표기(끊긴 링크 방지).
   */
  creatorHandle?: string;
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

/**
 * 배송지 스냅샷 — 물리 굿즈 주문의 배송 정보.
 * 서버 wire: ShippingIn(주문 생성 입력)·OrderShippingOut(주문 조회 스냅샷) 계약.
 */
export interface ShippingAddress {
  recipientName: string;
  recipientPhone: string;
  postalCode: string;
  address1: string;
  address2: string;
}

export interface Order {
  id: string;
  /** 표시용 주문 일자(YYYY-MM-DD). */
  createdAt: string;
  status: OrderStatus;
  items: OrderItem[];
  subtotal: number;
  /** 배송비 — 서버 산출(shipping_fee). 정책 확정 전 0원 고정(날조 금액 금지). */
  shipping: number;
  total: number;
  creatorName?: string;
  /** 배송지 스냅샷 — 배송 상품(굿즈) 주문에만(서버 OrderShippingOut). 있으면 주문 상세에 배송지 블록. */
  shippingAddress?: ShippingAddress;
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

/**
 * 스튜디오 대시보드 실 카운트 — 서버 StudioStatsOut(오너 스코프) 계약.
 * ※전부 정수 카운트다. 설계상 수익/정산/금액 필드는 없다(금액은 정산 게이트 ASS-229 —
 *   대시보드는 카운트만 소비하고 금액은 절대 날조하지 않는다).
 */
export interface StudioStats {
  /** 팔로워 수. */
  followers: number;
  /** 크리에이터 포스트 수. */
  posts: number;
  /** 보유 상품 수(전체 상태 포함). */
  products: number;
  /** 현재 판매중(공개 판매) 상품 수. */
  productsSelling: number;
  /** 유효 주문 건수(취소 제외 — 금액 아님). */
  orders: number;
  /** 활성 구독자 수(status=active). */
  subscribers: number;
}

/** 구독(멤버십) — 마이페이지 구독 관리. */
export interface Subscription {
  id: string;
  creatorId: string;
  creatorName: string;
  creatorHandle: string;
  /** 현재 티어 식별자(서버 SubscriptionOut.tier_id) — 프로필 멤버십 탭의 "구독 중" 판정·티어 전환용. */
  tierId?: string;
  tierName: string;
  price: number;
  period: string;
  /** 다음 결제일(YYYY-MM-DD). */
  nextBillingDate: string;
  status: "active" | "cancelled";
  /** 해지 예정 — 서버 계약: status=active 유지 + cancel_scheduled=true(말일 해지). */
  cancelScheduled?: boolean;
}
