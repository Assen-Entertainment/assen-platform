import { describe, it, expect } from "vitest";
import { vatBreakdown, shippingFor, summarizeProduct, summarizeTier, SHIPPING_FEE } from "./checkout";
import type { Product, MembershipTier } from "./api/types";

const goods: Product = { id: "p1", type: "goods", title: "아크릴 스탠드", price: 18000 };
const digital: Product = { id: "p2", type: "digital", title: "화보집", price: 9900 };
const tier: MembershipTier = { id: "t1", name: "스탠다드", price: 9900, period: "월", benefits: [] };

describe("checkout 요약 로직", () => {
  it("vatBreakdown: supply + vat = total (부가세 내재 10%)", () => {
    const { supply, vat } = vatBreakdown(11000);
    expect(supply + vat).toBe(11000);
    expect(vat).toBe(1000);
  });

  it("shippingFor: 굿즈만 배송비, 나머지 0", () => {
    expect(shippingFor("goods")).toBe(SHIPPING_FEE);
    expect(shippingFor("digital")).toBe(0);
    expect(shippingFor("membership")).toBe(0);
    expect(shippingFor("ticket")).toBe(0);
  });

  it("summarizeProduct: 굿즈는 수량 반영 + 배송비 부과", () => {
    const s = summarizeProduct(goods, 2);
    expect(s.qty).toBe(2);
    expect(s.subtotal).toBe(36000);
    expect(s.shipping).toBe(SHIPPING_FEE);
    expect(s.total).toBe(36000 + SHIPPING_FEE);
    expect(s.supply + s.vat).toBe(s.total);
  });

  it("summarizeProduct: 디지털은 배송비 0, 수량은 1 이상으로 클램프", () => {
    const s = summarizeProduct(digital, 0);
    expect(s.qty).toBe(1);
    expect(s.shipping).toBe(0);
    expect(s.total).toBe(9900);
  });

  it("summarizeTier: 멤버십은 배송 없음 + 라벨에 크리에이터명 포함", () => {
    const s = summarizeTier(tier, "별빛 일러스트");
    expect(s.kind).toBe("membership");
    expect(s.shipping).toBe(0);
    expect(s.total).toBe(9900);
    expect(s.label).toContain("별빛 일러스트");
  });
});
