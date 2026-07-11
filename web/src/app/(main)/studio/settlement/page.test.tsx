import * as React from "react";
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";

/**
 * ASS-289(#5) — 정산 뷰가 라이브 모드에서 mock 정산 금액을 렌더하지 않는지 검증한다.
 * USE_API는 모듈 로드 시 process.env.NEXT_PUBLIC_API_URL로 결정되므로, env 스텁 후
 * resetModules로 페이지를 재평가해 라이브/mock 분기를 각각 확인한다.
 */
afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

async function loadPage() {
  vi.resetModules();
  const mod = await import("./page");
  return mod.default;
}

describe("StudioSettlementPage", () => {
  it("라이브 모드에선 '정산 데이터 준비 중' 상태를 보여주고 mock 금액을 렌더하지 않는다", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.test");
    const Page = await loadPage();
    render(<Page />);

    expect(screen.getByText("정산 데이터 준비 중이에요")).toBeInTheDocument();
    // mock 정산 금액(총 판매액 1,840,000 / 실지급액 1,595,280)은 노출되지 않는다.
    expect(screen.queryByText("₩1,840,000")).not.toBeInTheDocument();
    expect(screen.queryByText("₩1,595,280")).not.toBeInTheDocument();
    // 데모 정산표도 렌더되지 않는다.
    expect(screen.queryByText("정산 내역 (데모)")).not.toBeInTheDocument();
  });

  it("mock 모드에선 데모로 라벨된 정산 수치를 보여준다", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    const Page = await loadPage();
    render(<Page />);

    // 데모 라벨 + mock 금액이 노출된다.
    expect(screen.getByText("정산 내역 (데모)")).toBeInTheDocument();
    expect(screen.getAllByText("₩1,840,000").length).toBeGreaterThan(0);
    expect(screen.getAllByText("₩1,595,280").length).toBeGreaterThan(0);
    // '준비 중' 상태는 아니다.
    expect(screen.queryByText("정산 데이터 준비 중이에요")).not.toBeInTheDocument();
  });
});
