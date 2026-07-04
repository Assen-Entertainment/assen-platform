import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StudioStatsGrid } from "./studio-stats";
import { qk } from "@/lib/api/queries";
import type { StudioStats } from "@/lib/api";

vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: { href: unknown; children: React.ReactNode }) => (
    <a href={typeof href === "string" ? href : "#"} {...p}>
      {children}
    </a>
  ),
}));

function wrap(qc: QueryClient, ui: React.ReactElement) {
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

// staleTime Infinity → 시드한 값만으로 렌더(마운트 refetch로 인한 시드 덮어쓰기 방지).
function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
}

const STATS: StudioStats = {
  followers: 12400,
  posts: 320,
  products: 6,
  productsSelling: 3,
  orders: 124,
  subscribers: 872,
};

describe("StudioStatsGrid", () => {
  it("실 카운트를 카드로 렌더하고 수익(금액) 카드는 노출하지 않는다", () => {
    const qc = makeClient();
    qc.setQueryData<StudioStats>(qk.studioStats, STATS);
    wrap(qc, <StudioStatsGrid />);

    // 라벨 + 실 카운트(ko-KR 천단위 포맷).
    expect(screen.getByText("팔로워")).toBeInTheDocument();
    expect(screen.getByText("12,400")).toBeInTheDocument();
    expect(screen.getByText("포스트")).toBeInTheDocument();
    expect(screen.getByText("320")).toBeInTheDocument();
    expect(screen.getByText("구독자")).toBeInTheDocument();
    expect(screen.getByText("872")).toBeInTheDocument();
    expect(screen.getByText("주문")).toBeInTheDocument();
    expect(screen.getByText("124")).toBeInTheDocument();

    // ★수익 카드/금액 없음 — 정산 게이트(날조 금지). "이번 달 수익" 라벨도, ₩ 금액도 없다.
    expect(screen.queryByText("이번 달 수익")).not.toBeInTheDocument();
    expect(screen.queryByText(/₩/)).not.toBeInTheDocument();
  });

  it("data가 null이면(비크리에이터/비로그인) 안내와 정산 링크를 보여준다(카운트 날조 안 함)", () => {
    const qc = makeClient();
    qc.setQueryData<StudioStats | null>(qk.studioStats, null);
    wrap(qc, <StudioStatsGrid />);

    expect(screen.getByText("통계를 불러올 수 없어요")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "정산 내역 보기" });
    expect(link).toHaveAttribute("href", "/studio/settlement");
    // 0 같은 날조 카운트 카드가 없다.
    expect(screen.queryByText("팔로워")).not.toBeInTheDocument();
  });
});
