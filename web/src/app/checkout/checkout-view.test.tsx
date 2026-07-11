import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CheckoutView } from "./checkout-view";
import { qk } from "@/lib/api/queries";
import { summarizeProduct } from "@/lib/checkout";
import type { Product } from "@/lib/api";

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

// 배송(굿즈) 결제 게이트(ASS-287)는 서버 capability(/api/capabilities)에 의존한다. 테스트는
// 캐시에 값을 시드해 게이트 개방/폐쇄를 결정적으로 재현한다(기본은 fail-closed=false).
function wrap(ui: React.ReactElement, opts?: { shippingAvailable?: boolean }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(qk.capabilities, {
    shippingCheckoutAvailable: opts?.shippingAvailable ?? false,
    paymentAvailable: true,
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const goods: Product = { id: "p1", type: "goods", title: "아크릴 스탠드", price: 8000, creatorName: "별빛", creatorHandle: "stellar" };
const digital: Product = { id: "p2", type: "digital", title: "화보집", price: 9900 };

describe("CheckoutView 금액 표시(서버 계약)", () => {
  it("날조 배송비/VAT 분리 행 없이 상품금액·무료 배송비·총액을 서버 계약대로 표기한다", () => {
    // subtotal 16000, shipping 0, total 16000. (배송 결제 개방 상태)
    wrap(<CheckoutView summary={summarizeProduct(goods, 2)} target={{ kind: "product", productId: "p1", qty: 2 }} />, {
      shippingAvailable: true,
    });
    // 행 합계 = 단가 × 수량.
    expect(screen.getByText("₩8,000 × 2개")).toBeInTheDocument();
    // 배송비는 무료(₩3,000 날조 금액 없음).
    expect(screen.getByText("무료")).toBeInTheDocument();
    // 공급가액/부가세 분리 행은 제거(가격=VAT 포함가 안내만 유지).
    expect(screen.queryByText("공급가액")).not.toBeInTheDocument();
    expect(screen.getByText("부가세(VAT 10%) 포함 금액입니다.")).toBeInTheDocument();
    // 총액 = subtotal(배송비 0) — 요약/버튼 등에 ₩16,000이 노출된다.
    expect(screen.getAllByText(/₩16,000/).length).toBeGreaterThan(0);
  });

  it("굿즈는 배송지 섹션을 노출한다(배송 결제 개방 시)", () => {
    wrap(<CheckoutView summary={summarizeProduct(goods, 1)} target={{ kind: "product", productId: "p1", qty: 1 }} />, {
      shippingAvailable: true,
    });
    expect(screen.getByLabelText("받는 분")).toBeInTheDocument();
    expect(screen.getByLabelText("주소")).toBeInTheDocument();
  });

  it("디지털 등 비배송 상품은 배송지 섹션을 노출하지 않는다", () => {
    wrap(<CheckoutView summary={summarizeProduct(digital, 1)} target={{ kind: "product", productId: "p2", qty: 1 }} />);
    expect(screen.queryByLabelText("받는 분")).not.toBeInTheDocument();
    expect(screen.queryByText("무료")).not.toBeInTheDocument();
  });

  it("배송지 미입력으로 결제 시도하면 필수 필드가 오류 상태로 표시된다", async () => {
    const user = userEvent.setup();
    wrap(<CheckoutView summary={summarizeProduct(goods, 1)} target={{ kind: "product", productId: "p1", qty: 1 }} />, {
      shippingAvailable: true,
    });
    // 결제 동의(버튼 활성화 조건) 후 결제 시도.
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /결제하기/ }));
    // 배송지 필수 필드가 오류(aria-invalid)로 전환된다(서버 422 전 클라 1차 검증).
    expect(screen.getByLabelText("받는 분")).toHaveAttribute("aria-invalid", "true");
  });
});

describe("CheckoutView 배송 결제 게이트(ASS-287 A-1)", () => {
  it("배송 결제가 준비 중이면 굿즈는 배송지 PII 폼 대신 준비 중 상태를 노출한다", () => {
    // shippingAvailable=false(기본, fail-closed).
    wrap(<CheckoutView summary={summarizeProduct(goods, 1)} target={{ kind: "product", productId: "p1", qty: 1 }} />);
    expect(screen.getByText("배송 결제 준비 중이에요")).toBeInTheDocument();
    // 배송지 PII 폼(받는 분·주소)·결제하기 버튼에 절대 도달하지 않는다.
    expect(screen.queryByLabelText("받는 분")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("주소")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /결제하기/ })).not.toBeInTheDocument();
  });

  it("파라미터 없는 데모 굿즈 폴백(target 없음)도 준비 중 상태로 수렴한다", () => {
    // page.tsx의 데모 굿즈 폴백(summarizeProduct(goods))처럼 target 없이 렌더 → PII 폼 대신 준비 중.
    wrap(<CheckoutView summary={summarizeProduct(goods, 1)} />);
    expect(screen.getByText("배송 결제 준비 중이에요")).toBeInTheDocument();
    expect(screen.queryByLabelText("받는 분")).not.toBeInTheDocument();
  });

  it("디지털 결제는 배송 게이트와 무관하게 그대로 동작한다(회귀 방지)", () => {
    // shippingAvailable=false 여도 디지털은 게이트되지 않는다.
    wrap(<CheckoutView summary={summarizeProduct(digital, 1)} target={{ kind: "product", productId: "p2", qty: 1 }} />);
    expect(screen.queryByText("배송 결제 준비 중이에요")).not.toBeInTheDocument();
    expect(screen.getByText("결제 수단")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /결제하기/ })).toBeInTheDocument();
  });
});
