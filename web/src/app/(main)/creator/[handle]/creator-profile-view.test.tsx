import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CreatorProfileView } from "./creator-profile-view";
import type { Creator, Post } from "@/lib/api";

// next/navigation·next/link — jsdom 렌더용 경량 목(라우팅 부수효과 제거).
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
  usePathname: () => "/creator/stellar",
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: { href: unknown; children: React.ReactNode }) => (
    <a href={typeof href === "string" ? href : "#"} {...p}>
      {children}
    </a>
  ),
}));

function wrap(ui: React.ReactElement) {
  // staleTime Infinity → initialData(props)만으로 렌더(마운트 refetch로 인한 blocked 뒤집힘 방지).
  const qc = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const blockedCreator: Creator = {
  id: "c1",
  name: "별빛 일러스트",
  handle: "stellar",
  followers: 100,
  following: false,
  blocked: true,
};
const post: Post = { id: "po1", creatorId: "c1", creatorName: "별빛 일러스트", likeCount: 1, commentCount: 0 };

describe("CreatorProfileView (차단됨)", () => {
  it("blocked면 차단 배너를 보여주고 포스트/탭 콘텐츠를 숨긴다", () => {
    wrap(<CreatorProfileView creator={blockedCreator} posts={[post]} products={[]} tiers={[]} />);
    // 배너 + 콘텐츠 숨김 안내가 노출된다.
    expect(screen.getByText("차단한 크리에이터예요")).toBeInTheDocument();
    expect(screen.getByText("콘텐츠를 숨기고 있어요")).toBeInTheDocument();
    // 탭(포스트/스토어/멤버십)은 렌더되지 않는다(콘텐츠 숨김).
    expect(screen.queryByRole("tab", { name: "포스트" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "스토어" })).not.toBeInTheDocument();
  });

  it("차단 상태에선 해제 버튼을 노출한다", () => {
    wrap(<CreatorProfileView creator={blockedCreator} posts={[]} products={[]} tiers={[]} />);
    expect(screen.getAllByRole("button", { name: "차단 해제" }).length).toBeGreaterThan(0);
  });
});
