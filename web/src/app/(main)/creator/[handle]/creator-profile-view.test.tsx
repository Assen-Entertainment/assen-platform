import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CreatorProfileView } from "./creator-profile-view";
import type { Creator, Post, MembershipTier } from "@/lib/api";

// next/navigation·next/link — jsdom 렌더용 경량 목(라우팅 부수효과 제거).
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
  usePathname: () => "/creator/stellar",
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: { href: unknown; children: React.ReactNode }) => (
    <a href={typeof href === "string" ? href : "/"} {...p}>
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
    wrap(<CreatorProfileView creator={blockedCreator} posts={{ items: [post] }} products={[]} tiers={[]} />);
    // 배너 + 콘텐츠 숨김 안내가 노출된다.
    expect(screen.getByText("차단한 크리에이터예요")).toBeInTheDocument();
    expect(screen.getByText("콘텐츠를 숨기고 있어요")).toBeInTheDocument();
    // 탭(포스트/스토어/멤버십)은 렌더되지 않는다(콘텐츠 숨김).
    expect(screen.queryByRole("tab", { name: "포스트" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "스토어" })).not.toBeInTheDocument();
  });

  it("차단 상태에선 해제 버튼을 노출한다", () => {
    wrap(<CreatorProfileView creator={blockedCreator} posts={{ items: [] }} products={[]} tiers={[]} />);
    expect(screen.getAllByRole("button", { name: "차단 해제" }).length).toBeGreaterThan(0);
  });
});

// 시드 mock 구독이 없는 핸들 — mySub 미존재를 보장해 신규 가입 CTA("구독하기")가 안정적으로 렌더된다.
// (stellar·rabbit 은 mock SUBSCRIPTIONS에 있어 "이 티어로 변경"으로 바뀌므로 피한다.)
const openCreator: Creator = {
  id: "c9",
  name: "새달 스튜디오",
  handle: "saedal-no-sub",
  followers: 100,
  following: false,
};
const tiers: MembershipTier[] = [
  { id: "t1", name: "라이트", price: 4900, period: "월", benefits: ["전용 포스트"] },
  { id: "t2", name: "스탠다드", price: 9900, period: "월", benefits: ["라이트 혜택 전부", "월간 라이브"] },
  { id: "t3", name: "프리미엄", price: 19900, period: "월", benefits: ["스탠다드 전부"] },
];

describe("CreatorProfileView (추천 티어 heuristic)", () => {
  it("서버 featured가 없어도 가운데 티어를 '추천'으로 승격하고 모든 구독 CTA를 노출한다", async () => {
    const user = userEvent.setup();
    // 시드가 featured를 전부 false로 주는 상황(뷰 레벨 heuristic이 앵커를 만든다).
    wrap(<CreatorProfileView creator={openCreator} posts={{ items: [] }} products={[]} tiers={tiers} />);
    // 멤버십 탭으로 전환(Radix Tabs는 비활성 콘텐츠를 언마운트).
    await user.click(screen.getByRole("tab", { name: "멤버십" }));
    // 3개 티어 중 가운데(index 1) 하나만 "추천" 배지로 강조된다.
    expect(screen.getAllByText("추천")).toHaveLength(1);
    // 모든 티어가 또렷한 구독 CTA를 갖는다(회색 secondary로 죽지 않음).
    expect(screen.getAllByRole("button", { name: "구독하기" })).toHaveLength(3);
  });

  it("서버가 featured 티어를 주면 heuristic 대신 그걸 존중한다", async () => {
    const user = userEvent.setup();
    // t1(첫 번째)을 서버가 featured로 지정 → 가운데(t2)가 아니라 t1이 앵커.
    const serverFeatured: MembershipTier[] = [
      { ...tiers[0], featured: true, badge: "인기" },
      tiers[1],
      tiers[2],
    ];
    wrap(<CreatorProfileView creator={openCreator} posts={{ items: [] }} products={[]} tiers={serverFeatured} />);
    await user.click(screen.getByRole("tab", { name: "멤버십" }));
    // 서버 badge("인기")가 노출되고, 뷰가 임의로 "추천"을 덧붙이지 않는다.
    expect(screen.getAllByText("인기")).toHaveLength(1);
    expect(screen.queryByText("추천")).not.toBeInTheDocument();
  });
});
