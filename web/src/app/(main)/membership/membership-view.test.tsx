import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MembershipView } from "./membership-view";
import type { Subscription } from "@/lib/api";

// next/navigation·next/link — jsdom 렌더용 경량 목.
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
  // staleTime Infinity → initialData(props)만으로 렌더(마운트 refetch 없음).
  const qc = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const sub: Subscription = {
  id: "s1",
  creatorId: "c1",
  creatorName: "별빛 일러스트",
  creatorHandle: "stellar",
  tierId: "t2",
  tierName: "스탠다드",
  price: 9900,
  period: "월",
  nextBillingDate: "2026-07-15",
  status: "active",
};

describe("MembershipView (내 멤버십 허브)", () => {
  it("활성 구독이 있으면 크리에이터·티어 카드와 관리/둘러보기 동선을 노출한다", () => {
    wrap(<MembershipView subscriptions={[sub]} />);
    expect(screen.getByText("별빛 일러스트")).toBeInTheDocument();
    expect(screen.getByText("스탠다드 멤버십")).toBeInTheDocument();
    expect(screen.getByText("다음 결제일")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "크리에이터 둘러보기" })).toBeInTheDocument();
    // 전역 요금표에서 직접 구독하는 CTA는 없다(구독은 크리에이터 컨텍스트에서만).
    expect(screen.queryByRole("button", { name: "구독하기" })).not.toBeInTheDocument();
  });

  it("구독이 없으면 가치 소개 + 둘러보기 CTA를 노출한다(직접 구독 요금표 없음)", () => {
    wrap(<MembershipView subscriptions={[]} />);
    expect(screen.getByRole("link", { name: "크리에이터 둘러보기" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "구독하기" })).not.toBeInTheDocument();
  });
});
