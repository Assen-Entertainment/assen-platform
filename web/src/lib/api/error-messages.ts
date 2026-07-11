import { ApiError } from "./client";

/**
 * 서버 `config.errors.ErrorCode` 미러 — 안정 code 식별자 단일 출처.
 * 뷰(로그인 등)의 code 분기는 매직스트링 대신 이 상수를 참조해 문구 매핑과 일원화한다.
 */
export const ERROR_CODES = {
  AccountNotRegistered: "AccountNotRegistered",
  OtpInvalid: "OtpInvalid",
  OwnerRequired: "OwnerRequired",
  ProductNotOrderable: "ProductNotOrderable",
  OutOfStock: "OutOfStock",
  InsufficientStock: "InsufficientStock",
  MembershipOnlyProduct: "MembershipOnlyProduct",
  ShippingAddressRequired: "ShippingAddressRequired",
  OrderNotCancellable: "OrderNotCancellable",
  OrderNotRefundable: "OrderNotRefundable",
  OpenRefundExists: "OpenRefundExists",
  DuplicateSubscription: "DuplicateSubscription",
  SubscriptionNotCancellable: "SubscriptionNotCancellable",
  SubscriptionNotActive: "SubscriptionNotActive",
  TierNotFound: "TierNotFound",
  TierInUse: "TierInUse",
  PaymentCardInvalid: "PaymentCardInvalid",
  PaymentMethodNotFound: "PaymentMethodNotFound",
  // 무료 획득 게이트(ASS-297) — 유료/무료 경로 교차 사용·무료 가격 불변식 위반 시 서버가 422로 거부.
  PricingNotFree: "PricingNotFree",
  PricingIsFree: "PricingIsFree",
  PricingFreeRequiresZeroPrice: "PricingFreeRequiresZeroPrice",
  // 배송(굿즈) 결제 게이트(ASS-287 A-1) — ENABLE_SHIPPING_CHECKOUT off 시 굿즈 주문을 503으로 거부.
  ShippingCheckoutUnavailable: "ShippingCheckoutUnavailable",
  InteractionBlocked: "InteractionBlocked",
  // 이미지 업로드(R12) — POST /api/uploads 실패 사유(서버 config.errors.ErrorCode 미러).
  UploadTypeUnsupported: "UploadTypeUnsupported",
  UploadTooLarge: "UploadTooLarge",
  UploadInvalid: "UploadInvalid",
  UploadStorageUnavailable: "UploadStorageUnavailable",
} as const;
export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];

/**
 * 서버 계약 error code → 한국어 사용자 문구(기본 매핑).
 *
 * 키는 `ERROR_CODES`(서버 `config.errors.ErrorCode` 미러)와 일치한다. 뷰별 특화 문구는
 * `apiErrorMessage`의 `fallbackMap` 인자로 오버라이드하고, 여기에 없는 code는 서버 `detail`(표시용)로
 * 폴백한다. ※문자열 부분일치 분기는 취약 — 분기·문구는 전부 이 안정 code 기준으로 일원화한다.
 */
export const ERROR_CODE_MESSAGES: Record<string, string> = {
  // 인증(identity)
  AccountNotRegistered: "가입되지 않은 번호예요. 회원가입을 먼저 진행해 주세요.",
  OtpInvalid: "인증번호가 올바르지 않아요. 다시 확인해 주세요.",
  OwnerRequired: "크리에이터 계정에서만 할 수 있어요.",
  // 커머스(주문/상품)
  ProductNotOrderable: "지금은 주문할 수 없는 상품이에요.",
  OutOfStock: "품절된 상품이에요.",
  InsufficientStock: "재고가 부족해요. 수량을 줄여 다시 시도해 주세요.",
  MembershipOnlyProduct: "멤버십 전용 상품이에요. 먼저 멤버십에 가입해 주세요.",
  ShippingAddressRequired: "배송지를 입력해 주세요. 배송 상품은 받는 분·연락처·주소가 필요해요.",
  OrderNotCancellable: "이 주문은 취소할 수 없는 상태예요.",
  OrderNotRefundable: "이 주문은 환불할 수 없는 상태예요.",
  OpenRefundExists: "이미 진행 중인 환불 신청이 있어요.",
  // 멤버십(구독/티어)
  DuplicateSubscription: "이미 구독 중인 멤버십이에요.",
  SubscriptionNotCancellable: "이 구독은 해지할 수 없는 상태예요.",
  SubscriptionNotActive: "진행 중인 구독만 티어를 변경할 수 있어요.",
  TierNotFound: "멤버십 티어를 찾을 수 없어요.",
  TierInUse: "구독자가 있는 티어는 삭제할 수 없어요.",
  // 결제수단
  PaymentCardInvalid: "카드 정보가 올바르지 않아요. 다시 확인해 주세요.",
  PaymentMethodNotFound: "결제수단을 찾을 수 없어요.",
  // 무료 획득 게이트(ASS-297)
  PricingNotFree: "무료로 받을 수 없는 상품이에요. 결제가 필요해요.",
  PricingIsFree: "무료로 제공되는 상품이에요. 무료 받기로 진행해 주세요.",
  PricingFreeRequiresZeroPrice: "무료로 설정하려면 가격을 0원으로 맞춰 주세요.",
  // 배송 결제 준비 중(ASS-287): 배송 상품 결제 흐름이 아직 열리지 않았어요(정책 게이트).
  ShippingCheckoutUnavailable: "배송 상품 결제가 아직 준비 중이에요. 잠시 후 다시 시도해 주세요.",
  // 개인 차단(R4): 차단한 크리에이터 콘텐츠에 like/댓글/주문 시 서버가 422로 거부.
  InteractionBlocked: "차단한 크리에이터의 콘텐츠에는 상호작용할 수 없어요.",
  // 이미지 업로드(R12): POST /api/uploads 실패 — 파일형식(415)·크기(413)·거부(422)·준비중(503).
  UploadTypeUnsupported: "이미지 파일(PNG·JPEG·WEBP·GIF)만 올릴 수 있어요.",
  UploadTooLarge: "파일이 너무 커요. 더 작은 이미지를 올려 주세요.",
  UploadInvalid: "이미지를 올릴 수 없어요. 손상됐거나 허용되지 않는 파일이에요.",
  UploadStorageUnavailable: "이미지 업로드가 아직 준비 중이에요. 잠시 후 다시 시도해 주세요.",
};

/**
 * ApiError → 사용자 안내 문구. 우선순위: `fallbackMap[code]` → `ERROR_CODE_MESSAGES[code]`
 * → 서버 `detail`(표시용 폴백) → `fallback`. ApiError가 아니면 곧바로 `fallback`.
 *
 * @param fallbackMap 뷰별 특화 code→문구(기본 매핑보다 우선).
 * @param fallback code·detail이 모두 없을 때의 최후 문구.
 */
export function apiErrorMessage(
  e: unknown,
  fallbackMap?: Record<string, string>,
  fallback = "잠시 후 다시 시도해 주세요.",
): string {
  if (e instanceof ApiError) {
    const code = e.code;
    if (code) {
      const mapped = fallbackMap?.[code] ?? ERROR_CODE_MESSAGES[code];
      if (mapped) return mapped;
    }
    if (e.detail) return e.detail;
  }
  return fallback;
}
