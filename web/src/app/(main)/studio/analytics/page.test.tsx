import * as React from "react";
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";

/**
 * ASS-289(#5) — 애널리틱스 뷰가 라이브 모드에서 mock 수익/수치를 렌더하지 않는지 검증한다.
 * 차트는 next/dynamic으로 지연 로드되므로 단위 테스트에선 null 스텁으로 대체(동기 렌더 안정화) —
 * 검증 대상은 게이트 분기와 StatItem 수치(동기 렌더)다.
 */
vi.mock("next/dynamic", () => ({
  default: () => () => null,
}));

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

async function loadPage() {
  vi.resetModules();
  const mod = await import("./page");
  return mod.default;
}

describe("StudioAnalyticsPage", () => {
  it("라이브 모드에선 '애널리틱스 데이터 준비 중' 상태를 보여주고 mock 수익을 렌더하지 않는다", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.test");
    const Page = await loadPage();
    render(<Page />);

    expect(screen.getByText("애널리틱스 데이터 준비 중이에요")).toBeInTheDocument();
    // mock 월 수익(1,840,000)·구독자 수치가 노출되지 않는다.
    expect(screen.queryByText("₩1,840,000")).not.toBeInTheDocument();
    expect(screen.queryByText("월 수익")).not.toBeInTheDocument();
  });

  it("mock 모드에선 데모로 라벨된 수익/구독자 추이를 보여준다", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    const Page = await loadPage();
    render(<Page />);

    // 데모 라벨 + mock 수익/구독자 수치가 노출된다.
    expect(screen.getByText("데모 데이터 — 실 수치가 아니에요")).toBeInTheDocument();
    // "월 수익"은 StatItem 라벨 + 차트 카드 제목으로 2회 등장.
    expect(screen.getAllByText("월 수익").length).toBeGreaterThan(0);
    expect(screen.getByText("₩1,840,000")).toBeInTheDocument();
    expect(screen.getByText("872")).toBeInTheDocument();
    // '준비 중' 상태는 아니다.
    expect(screen.queryByText("애널리틱스 데이터 준비 중이에요")).not.toBeInTheDocument();
  });
});
