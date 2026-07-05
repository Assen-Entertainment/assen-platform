import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import StudioPostsPage from "./page";
import { ApiError, type Post } from "@/lib/api";
import { useStudioPosts } from "@/lib/api/queries";

// next/link — jsdom 렌더용 경량 목.
vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: { href: unknown; children: React.ReactNode }) => (
    <a href={typeof href === "string" ? href : "#"} {...p}>
      {children}
    </a>
  ),
}));

// useStudioPosts만 목으로 상태를 구동(오너 목록·빈 상태·403). 뮤테이션 훅은 실제(QueryClient 필요).
vi.mock("@/lib/api/queries", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api/queries")>();
  return { ...actual, useStudioPosts: vi.fn() };
});

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

type StudioPostsReturn = ReturnType<typeof useStudioPosts>;
function hookState(over: Partial<StudioPostsReturn>): StudioPostsReturn {
  return {
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isFetchingNextPage: false,
    ...over,
  } as unknown as StudioPostsReturn;
}

const posts: Post[] = [
  { id: "po1", creatorId: "c1", creatorName: "별빛 일러스트", body: "신작 공개! 많은 관심 부탁드려요.", likeCount: 842, commentCount: 2 },
  { id: "po2", creatorId: "c1", creatorName: "별빛 일러스트", body: "성인 전용 러프 스케치", likeCount: 10, commentCount: 0, isAdult: true },
];

describe("StudioPostsPage (오너 스코프)", () => {
  beforeEach(() => vi.mocked(useStudioPosts).mockReset());

  it("오너 목록을 렌더하고 19+ 포스트에 배지를 노출한다(소비자 게이트 미적용)", () => {
    vi.mocked(useStudioPosts).mockReturnValue(hookState({ data: posts }));
    wrap(<StudioPostsPage />);
    expect(screen.getByText(/신작 공개/)).toBeInTheDocument();
    // 오너 뷰는 19+도 표시 — 소비자 게이트 재사용으로 오너 19+가 안 보이던 결함 회귀 방지.
    expect(screen.getByText("19+")).toBeInTheDocument();
  });

  it("빈 목록이면 안내와 새 포스트 CTA를 보여준다", () => {
    vi.mocked(useStudioPosts).mockReturnValue(hookState({ data: [] }));
    wrap(<StudioPostsPage />);
    expect(screen.getByText("아직 발행한 포스트가 없어요")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "새 포스트 작성" })).toBeInTheDocument();
  });

  it("403(비크리에이터)은 방어 안내를 보여준다(빈 목록과 구분)", () => {
    vi.mocked(useStudioPosts).mockReturnValue(
      hookState({ isError: true, error: new ApiError(403, "API 403", undefined, "OwnerRequired") }),
    );
    wrap(<StudioPostsPage />);
    expect(screen.getByText("크리에이터 계정이 필요해요")).toBeInTheDocument();
    // 빈 목록 문구는 나오지 않는다(상태 구분).
    expect(screen.queryByText("아직 발행한 포스트가 없어요")).not.toBeInTheDocument();
  });
});
