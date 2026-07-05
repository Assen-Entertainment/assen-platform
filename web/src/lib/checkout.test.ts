import { describe, it, expect } from "vitest";
import { shippingFor, needsShippingAddress, summarizeProduct, summarizeTier, SHIPPING_FEE } from "./checkout";
import type { Creator, Product, MembershipTier } from "./api/types";

const goods: Product = { id: "p1", type: "goods", title: "아크릴 스탠드", price: 18000, creatorName: "별빛 일러스트", creatorHandle: "stellar" };
const digital: Product = { id: "p2", type: "digital", title: "화보집", price: 9900 };
const tier: MembershipTier = { id: "t1", name: "스탠다드", price: 9900, period: "월", benefits: [] };
const creator: Creator = { id: "c1", name: "별빛 일러스트", handle: "stellar", followers: 100, accentColor: "#E14B8A" };

describe("checkout 요약 로직", () => {
  it("배송비는 정책상 0원 고정(날조 금액 없음)", () => {
    expect(SHIPPING_FEE).toBe(0);
    expect(shippingFor("goods")).toBe(0);
    expect(shippingFor("digital")).toBe(0);
  });

  it("needsShippingAddress: 굿즈만 배송지 필요, 나머지는 불필요", () => {
    expect(needsShippingAddress("goods")).toBe(true);
    expect(needsShippingAddress("digital")).toBe(false);
    expect(needsShippingAddress("ticket")).toBe(false);
    expect(needsShippingAddress("membership")).toBe(false);
  });

  it("summarizeProduct: 금액은 서버 계약(subtotal + shipping = total)을 미러하고 배송비는 0", () => {
    const s = summarizeProduct(goods, 2);
    expect(s.qty).toBe(2);
    expect(s.subtotal).toBe(36000);
    expect(s.shipping).toBe(0);
    // 서버 계약 항등식: subtotal + shipping = total (배송비 0이므로 total = subtotal).
    expect(s.subtotal + s.shipping).toBe(s.total);
    expect(s.total).toBe(36000);
    // 배송지 스텝·스토어 연결용 메타.
    expect(s.productType).toBe("goods");
    expect(s.creatorName).toBe("별빛 일러스트");
    expect(s.creatorHandle).toBe("stellar");
  });

  it("summarizeProduct: 디지털은 배송비 0, 수량은 1 이상으로 클램프", () => {
    const s = summarizeProduct(digital, 0);
    expect(s.qty).toBe(1);
    expect(s.shipping).toBe(0);
    expect(s.total).toBe(9900);
    expect(s.productType).toBe("digital");
  });

  it("summarizeTier: 멤버십은 배송 없음 + 크리에이터/티어를 명시(결제 확인 노출용)", () => {
    const s = summarizeTier(tier, creator);
    expect(s.kind).toBe("membership");
    expect(s.shipping).toBe(0);
    expect(s.total).toBe(9900);
    expect(s.label).toContain("별빛 일러스트");
    expect(s.creatorName).toBe("별빛 일러스트");
    expect(s.creatorHandle).toBe("stellar");
    expect(s.tierName).toBe("스탠다드");
  });
});
