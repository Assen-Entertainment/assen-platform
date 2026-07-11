import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MembershipView } from "./membership-view";
import type { Subscription } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
  usePathname: () => "/membership",
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: { href: unknown; children: React.ReactNode }) => (
    <a href={typeof href === "string" ? href : "/"} {...p}>
      {children}
    </a>
  ),
}));

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const freeSub: Subscription = {
  id: "sf1",
  creatorId: "c1",
  creatorName: "별빛 일러스트",
  creatorHandle: "stellar",
  tierId: "tf1",
  tierName: "무료팬",
  price: 0,
  period: "월",
  // 무료 멤버십은 결제 앵커가 없어 null.
  nextBillingDate: null,
  status: "active",
  isFree: true,
};

describe("MembershipView 무료 멤버십(ASS-297)", () => {
  it("무료 멤버십은 '무료 멤버십' 배지를 노출하고 결제일·결제 금액 행을 숨긴다", () => {
    wrap(<MembershipView subscriptions={[freeSub]} />);
    expect(screen.getByText("무료 멤버십")).toBeInTheDocument();
    // 결제일·결제 금액 행은 노출하지 않는다.
    expect(screen.queryByText("다음 결제일")).not.toBeInTheDocument();
    expect(screen.queryByText("결제 금액")).not.toBeInTheDocument();
    // 여전히 구독 중 상태는 표기한다.
    expect(screen.getByText("구독 중")).toBeInTheDocument();
  });
});
