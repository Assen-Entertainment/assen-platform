/**
 * 체크아웃 요약 계산 — 순수 함수(UI 무관, 단위 테스트 대상).
 *
 * ※ 실결제/PG 연동은 대표·법무 게이트, 본 계산은 UI mock 데모용이다.
 *   VAT·배송비·세금 정책 수치는 placeholder이며 단독 확정 대상이 아니다.
 */
import type { MembershipTier, Product } from "./api/types";

/** 물리 굿즈 기본 배송비(placeholder). 디지털/쿠폰/티켓/체험/멤버십은 무료. */
export const SHIPPING_FEE = 3000;

export interface OrderSummary {
  /** 대상 표기(상품명 또는 "티어 · 크리에이터"). */
  label: string;
  /** 결제 종류 — 단건 상품 / 정기 멤버십. */
  kind: "product" | "membership";
  unitPrice: number;
  qty: number;
  subtotal: number;
  shipping: number;
  total: number;
  /** 부가세 분리(placeholder) — 총액 내재 10% 가정. */
  supply: number;
  vat: number;
  /** 선택 옵션(상품 상세에서 전달, 있을 때만). */
  option?: string;
}

/** 부가세 분리 — 총액에 10% 부가세가 포함됐다고 가정(supply + vat = total). placeholder. */
export function vatBreakdown(total: number): { supply: number; vat: number } {
  const vat = Math.round(total / 11);
  return { supply: total - vat, vat };
}

/** 물리 굿즈만 배송비 부과. 그 외(디지털/쿠폰/티켓/체험/멤버십) 무료. */
export function shippingFor(type: Product["type"]): number {
  return type === "goods" ? SHIPPING_FEE : 0;
}

/** 상품 단건 주문 요약. qty는 1 이상으로 클램프. option은 있을 때만 요약에 담는다. */
export function summarizeProduct(product: Product, qty: number, option?: string): OrderSummary {
  const q = Math.max(1, Math.floor(qty) || 1);
  const subtotal = product.price * q;
  const shipping = shippingFor(product.type);
  const total = subtotal + shipping;
  const { supply, vat } = vatBreakdown(total);
  const opt = option?.trim();
  return {
    label: product.title,
    kind: "product",
    unitPrice: product.price,
    qty: q,
    subtotal,
    shipping,
    total,
    supply,
    vat,
    option: opt || undefined,
  };
}

/** 멤버십(정기결제) 주문 요약. 배송 없음, 수량 1 고정. */
export function summarizeTier(tier: MembershipTier, creatorName?: string): OrderSummary {
  const total = tier.price;
  const { supply, vat } = vatBreakdown(total);
  return {
    label: creatorName ? `${tier.name} · ${creatorName}` : tier.name,
    kind: "membership",
    unitPrice: tier.price,
    qty: 1,
    subtotal: total,
    shipping: 0,
    total,
    supply,
    vat,
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
