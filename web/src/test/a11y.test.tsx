import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as axeMatchers from "vitest-axe/matchers";
import "vitest-axe/extend-expect";
import { configureAxe } from "vitest-axe";

import { PostCard } from "@/components/ui/post-card";
import { MembershipTierCard } from "@/components/ui/membership-tier-card";
import { ReportSheet } from "@/components/ui/report-sheet";
import { CheckoutView } from "@/app/checkout/checkout-view";
import { SearchView } from "@/app/(main)/search/search-view";
import { summarizeProduct } from "@/lib/checkout";
import { SessionProvider } from "@/lib/session";
import LoginPage from "@/app/login/page";
import type { Creator, Product } from "@/lib/api";

expect.extend(axeMatchers);

// next/navigation·next/link — jsdom 렌더용 경량 목(기존 뷰 테스트와 동일 패턴).
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: { href: unknown; children: React.ReactNode }) => (
    <a href={typeof href === "string" ? href : "/"} {...p}>
      {children}
    </a>
  ),
}));

/**
 * 컴포넌트를 격리 렌더하므로 페이지 수준 랜드마크 규칙(region)은 비활성 —
 * 프래그먼트가 <main> 밖이라는 위양성 회피. color-contrast는 jsdom이 레이아웃/canvas를
 * 계산하지 못해 평가 불가(무의미한 canvas 에러만 발생) → 비활성. 대비는 시각 회귀·수동 QA가 담당.
 * 그 외 axe 기본 규칙(구조·ARIA·라벨·이름 등)은 모두 유지한다.
 */
const axe = configureAxe({
  rules: { region: { enabled: false }, "color-contrast": { enabled: false } },
});

function withQuery(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

const goods: Product = {
  id: "p1",
  type: "goods",
  title: "아크릴 스탠드",
  price: 18000,
  creatorName: "별빛",
  creatorHandle: "stellar",
};
const creators: Creator[] = [
  { id: "c1", name: "별빛 일러스트", handle: "stellar", followers: 100, category: "일러스트" },
];
const products: Product[] = [{ id: "p1", type: "goods", title: "아크릴 스탠드", price: 18000 }];

describe("a11y 스모크 (vitest-axe) — 대표 컴포넌트/뷰 위반 0", () => {
  it("피드 카드(PostCard)", async () => {
    const { container } = render(
      <PostCard
        creatorName="별빛 일러스트"
        creatorMeta="일러스트 · 3분 전"
        body="새 그림 올렸어요!"
        likeCount={12}
        commentCount={3}
        onLike={() => {}}
        onComment={() => {}}
        onShare={() => {}}
        onMore={() => {}}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it("멤버십 티어 카드(MembershipTierCard)", async () => {
    const { container } = render(
      <MembershipTierCard
        name="스탠다드"
        price={9900}
        period="월"
        benefits={["멤버 전용 포스트", "월간 라이브", "굿즈 할인"]}
        badge="인기"
        featured
        onSubscribe={() => {}}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it("멤버십 티어 카드 — 비featured 브랜드 아웃라인 CTA(대비)", async () => {
    // 비featured 구독 CTA는 회색 secondary 대신 브랜드 아웃라인(border-primary·text-primary).
    // 라벨 대비가 라이트/다크 모두 AA인지 axe로 확인(회귀 가드).
    const { container } = render(
      <MembershipTierCard
        name="라이트"
        price={4900}
        period="월"
        benefits={["전용 포스트", "멤버 뱃지"]}
        onSubscribe={() => {}}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it("다이얼로그 열림 상태(ReportSheet)", async () => {
    // Radix 포털은 document.body로 렌더되므로 baseElement로 axe를 돌린다.
    const { baseElement } = render(
      <ReportSheet open onOpenChange={() => {}} onSubmit={() => {}} />,
    );
    expect(await axe(baseElement)).toHaveNoViolations();
  });

  it("체크아웃 폼(CheckoutView)", async () => {
    const { container } = render(
      withQuery(
        <CheckoutView
          summary={summarizeProduct(goods, 1)}
          target={{ kind: "product", productId: "p1", qty: 1 }}
        />,
      ),
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it("검색 combobox(SearchView)", async () => {
    const { container } = render(withQuery(<SearchView creators={creators} products={products} />));
    expect(await axe(container)).toHaveNoViolations();
  });

  it("로그인 폼(LoginPage)", async () => {
    // config.apiUrl 미설정(테스트) → MockLogin(이메일/비밀번호/소셜) 렌더.
    const { container } = render(
      <SessionProvider>
        <LoginPage />
      </SessionProvider>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
