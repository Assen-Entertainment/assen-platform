import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CheckoutView } from "./checkout-view";
import { qk } from "@/lib/api/queries";
import { summarizeProduct, summarizeTier } from "@/lib/checkout";
import type { Product, MembershipTier, Creator } from "@/lib/api";

// next/navigation·next/link — jsdom 렌더용 경량 목.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: { href: unknown; children: React.ReactNode }) => (
    <a href={typeof href === "string" ? href : "/"} {...p}>
      {children}
    </a>
  ),
}));

function wrap(ui: React.ReactElement, opts?: { shippingAvailable?: boolean }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(qk.capabilities, {
    shippingCheckoutAvailable: opts?.shippingAvailable ?? false,
    paymentAvailable: true,
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

// 무료 획득 대상(pricing_kind=free) — 가격 0 + 무료 플래그.
const freeDigital: Product = { id: "pf1", type: "digital", title: "무료 화보", price: 0, pricingKind: "free" };
const freeGoods: Product = { id: "pf2", type: "goods", title: "무료 스티커", price: 0, pricingKind: "free" };
const freeTier: MembershipTier = { id: "tf1", name: "무료팬", price: 0, period: "월", benefits: ["전용 포스트"], pricingKind: "free" };
const creator: Creator = { id: "c1", name: "별빛", handle: "stellar", followers: 100 };

describe("CheckoutView 무료 획득(ASS-297)", () => {
  it("무료 상품은 결제수단 선택기를 숨기고 CTA를 '무료로 받기'로 표기한다", () => {
    wrap(<CheckoutView summary={summarizeProduct(freeDigital, 1)} target={{ kind: "product", productId: "pf1", qty: 1 }} />);
    // 결제수단 선택기·VAT 안내는 노출하지 않는다(결제 자체가 없음).
    expect(screen.queryByText("결제 수단")).not.toBeInTheDocument();
    expect(screen.queryByText("부가세(VAT 10%) 포함 금액입니다.")).not.toBeInTheDocument();
    // CTA는 무료 받기.
    expect(screen.getByRole("button", { name: "무료로 받기" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /결제하기/ })).not.toBeInTheDocument();
    // 금액 요약은 무료로 표기한다.
    expect(screen.getAllByText("무료").length).toBeGreaterThan(0);
  });

  it("무료 굿즈는 결제만 빠지고 배송지 폼은 유지한다(배송 게이트 개방 시)", () => {
    wrap(<CheckoutView summary={summarizeProduct(freeGoods, 1)} target={{ kind: "product", productId: "pf2", qty: 1 }} />, {
      shippingAvailable: true,
    });
    // 배송지 폼은 그대로(무료는 결제만 뺀다).
    expect(screen.getByLabelText("받는 분")).toBeInTheDocument();
    expect(screen.getByLabelText("주소")).toBeInTheDocument();
    // 결제수단 선택기는 없음.
    expect(screen.queryByText("결제 수단")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "무료로 받기" })).toBeInTheDocument();
  });

  it("무료 굿즈도 배송 게이트가 닫혀 있으면 준비 중 상태로 수렴한다(배송 PII 폼 도달 차단)", () => {
    // shippingAvailable=false(기본). 무료여도 배송 게이트는 그대로 적용.
    wrap(<CheckoutView summary={summarizeProduct(freeGoods, 1)} target={{ kind: "product", productId: "pf2", qty: 1 }} />);
    expect(screen.getByText("배송 결제 준비 중이에요")).toBeInTheDocument();
    expect(screen.queryByLabelText("받는 분")).not.toBeInTheDocument();
  });

  it("무료 멤버십은 결제수단·자동결제 동의를 숨기고 CTA를 '무료로 시작하기'로 표기한다", () => {
    wrap(<CheckoutView summary={summarizeTier(freeTier, creator)} target={{ kind: "membership", tierId: "tf1" }} />);
    expect(screen.queryByText("결제 수단")).not.toBeInTheDocument();
    // 자동결제 동의 시트(매월 자동결제)는 노출하지 않는다.
    expect(screen.queryByText(/자동결제/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "무료로 시작하기" })).toBeInTheDocument();
  });
});
