import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CheckoutView } from "./checkout-view";
import { summarizeProduct } from "@/lib/checkout";
import type { Product } from "@/lib/api";

// next/navigation·next/link — jsdom 렌더용 경량 목.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: { href: unknown; children: React.ReactNode }) => (
    <a href={typeof href === "string" ? href : "#"} {...p}>
      {children}
    </a>
  ),
}));

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const goods: Product = { id: "p1", type: "goods", title: "아크릴 스탠드", price: 8000, creatorName: "별빛", creatorHandle: "stellar" };
const digital: Product = { id: "p2", type: "digital", title: "화보집", price: 9900 };

describe("CheckoutView 금액 표시(서버 계약)", () => {
  it("날조 배송비/VAT 분리 행 없이 상품금액·무료 배송비·총액을 서버 계약대로 표기한다", () => {
    // subtotal 16000, shipping 0, total 16000.
    wrap(<CheckoutView summary={summarizeProduct(goods, 2)} target={{ kind: "product", productId: "p1", qty: 2 }} />);
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

  it("굿즈는 배송지 섹션을 노출한다", () => {
    wrap(<CheckoutView summary={summarizeProduct(goods, 1)} target={{ kind: "product", productId: "p1", qty: 1 }} />);
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
    wrap(<CheckoutView summary={summarizeProduct(goods, 1)} target={{ kind: "product", productId: "p1", qty: 1 }} />);
    // 결제 동의(버튼 활성화 조건) 후 결제 시도.
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /결제하기/ }));
    // 배송지 필수 필드가 오류(aria-invalid)로 전환된다(서버 422 전 클라 1차 검증).
    expect(screen.getByLabelText("받는 분")).toHaveAttribute("aria-invalid", "true");
  });
});
