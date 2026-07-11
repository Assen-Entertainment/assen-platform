/**
 * 체크아웃 요약 계산 — 순수 함수(UI 무관, 단위 테스트 대상).
 *
 * ※ 실결제/PG 연동은 대표·법무 게이트, 본 계산은 UI mock 데모용이다.
 *   금액은 서버 계약(subtotal + shipping = total)을 그대로 미러한다 — 클라에서
 *   배송비/VAT를 날조하지 않는다(KR 관행상 표시가는 VAT 포함가이므로 별도 VAT 행 없음).
 */
import type { Creator, MembershipTier, Product } from "./api/types";

/** 배송비 — 정책 확정 전 0원 고정(정책 게이트). 굿즈도 현재는 무료(날조 금액 금지). */
export const SHIPPING_FEE = 0;

export interface OrderSummary {
  /** 대상 표기(상품명 또는 "티어 · 크리에이터"). */
  label: string;
  /** 결제 종류 — 단건 상품 / 정기 멤버십. */
  kind: "product" | "membership";
  unitPrice: number;
  qty: number;
  subtotal: number;
  /** 배송비 — 서버 계약 미러(현재 정책상 0). */
  shipping: number;
  total: number;
  /** 선택 옵션(상품 상세에서 전달, 있을 때만). */
  option?: string;
  /** 상품 종류 — 배송지 스텝(goods) 노출 판단·표기용. 멤버십은 없음. */
  productType?: Product["type"];
  /**
   * 무료 획득 대상(pricing_kind=free) — true면 결제 없이 무료 받기/시작하기(ASS-297). 체크아웃이
   * 결제수단 UI를 숨기고 무료 hook(createOrderFree/subscribeFree)을 호출한다. 배송(굿즈)은 유지.
   */
  free?: boolean;
  /** 멤버십 결제 확인용 — 대상 크리에이터/티어를 명시(대상 불투명 해소). */
  creatorName?: string;
  creatorHandle?: string;
  tierName?: string;
}

/** 배송비 — 정책 확정 전 0원 고정(모든 타입). */
export function shippingFor(_type: Product["type"]): number {
  return SHIPPING_FEE;
}

/** 물리 굿즈 주문은 배송지 입력이 필요하다(체크아웃 배송지 스텝 노출 판단). */
export function needsShippingAddress(type: Product["type"]): boolean {
  return type === "goods";
}

/** 상품 단건 주문 요약. qty는 1 이상으로 클램프. option은 있을 때만 요약에 담는다. */
export function summarizeProduct(product: Product, qty: number, option?: string): OrderSummary {
  const q = Math.max(1, Math.floor(qty) || 1);
  const subtotal = product.price * q;
  const shipping = shippingFor(product.type);
  const total = subtotal + shipping;
  const opt = option?.trim();
  return {
    label: product.title,
    kind: "product",
    unitPrice: product.price,
    qty: q,
    subtotal,
    shipping,
    total,
    option: opt || undefined,
    productType: product.type,
    creatorName: product.creatorName,
    creatorHandle: product.creatorHandle,
    free: product.pricingKind === "free",
  };
}

/** 멤버십(정기결제) 주문 요약. 배송 없음, 수량 1 고정. 크리에이터/티어를 명시해 결제 확인에 노출. */
export function summarizeTier(tier: MembershipTier, creator?: Creator): OrderSummary {
  const total = tier.price;
  return {
    label: creator?.name ? `${tier.name} · ${creator.name}` : tier.name,
    kind: "membership",
    unitPrice: tier.price,
    qty: 1,
    subtotal: total,
    shipping: 0,
    total,
    creatorName: creator?.name,
    creatorHandle: creator?.handle,
    tierName: tier.name,
    free: tier.pricingKind === "free",
  };
}

/** mock 주문번호 생성 — ASN-XXXXXX(6자리). 실 발번은 백엔드 게이트. */
export function mockOrderId(): string {
  return `ASN-${Math.floor(100000 + Math.random() * 900000)}`;
}

/** ₩ 접두 원화 표기. */
export function won(v: number): string {
  return "₩" + v.toLocaleString("ko-KR");
}
