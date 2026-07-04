import { ApiError } from "./client";

/**
 * 서버 계약 error code → 한국어 사용자 문구(기본 매핑).
 *
 * 서버 `config.errors.ErrorCode`를 미러한다. 뷰별 특화 문구는 `apiErrorMessage`의
 * `fallbackMap` 인자로 오버라이드하고, 여기에 없는 code는 서버 `detail`(표시용)로 폴백한다.
 * ※문자열 부분일치 분기는 취약 — 분기·문구는 전부 이 안정 code 기준으로 일원화한다.
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
  OrderNotCancellable: "이 주문은 취소할 수 없는 상태예요.",
  OrderNotRefundable: "이 주문은 환불할 수 없는 상태예요.",
  OpenRefundExists: "이미 진행 중인 환불 신청이 있어요.",
  // 멤버십(구독/티어)
  DuplicateSubscription: "이미 구독 중인 멤버십이에요.",
  SubscriptionNotCancellable: "이 구독은 해지할 수 없는 상태예요.",
  TierNotFound: "멤버십 티어를 찾을 수 없어요.",
  TierInUse: "구독자가 있는 티어는 삭제할 수 없어요.",
  // 결제수단
  PaymentCardInvalid: "카드 정보가 올바르지 않아요. 다시 확인해 주세요.",
  PaymentMethodNotFound: "결제수단을 찾을 수 없어요.",
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
      if (fallbackMap && code in fallbackMap) return fallbackMap[code];
      if (code in ERROR_CODE_MESSAGES) return ERROR_CODE_MESSAGES[code];
    }
    if (e.detail) return e.detail;
  }
  return fallback;
}
