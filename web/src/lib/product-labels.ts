import type { MonetizableItemType } from "@/components/ui";

/**
 * 상품 타입 → 한글 라벨(6타입 공용).
 * product-detail-view·order-detail-view·studio/products 3곳에서 공유(중복 정의 제거).
 */
export const PRODUCT_TYPE_LABEL: Record<MonetizableItemType, string> = {
  goods: "굿즈",
  digital: "디지털",
  experience: "체험",
  ticket: "티켓",
  coupon: "쿠폰",
  membership: "멤버십",
};
