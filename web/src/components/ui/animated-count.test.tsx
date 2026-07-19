import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnimatedCount } from "./animated-count";

afterEach(() => {
  // matchMedia 목 정리(다른 테스트 격리).
  // @ts-expect-error 테스트 정리
  delete window.matchMedia;
});

describe("AnimatedCount — 살아있는 숫자", () => {
  it("초기 값을 즉시 포맷해 렌더한다(ko-KR 천단위)", () => {
    render(<AnimatedCount value={12400} />);
    expect(screen.getByText("12,400")).toBeInTheDocument();
  });

  it("커스텀 포맷을 적용한다", () => {
    render(<AnimatedCount value={5} format={(n) => `${n}명`} />);
    expect(screen.getByText("5명")).toBeInTheDocument();
  });

  it("reduced-motion에서는 값 변경 시 틱업 없이 즉시 새 값으로 갱신한다(CLS 0)", async () => {
    window.matchMedia = vi.fn().mockImplementation((q: string) => ({
      matches: true,
      media: q,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })) as unknown as typeof window.matchMedia;

    const { rerender } = render(<AnimatedCount value={100} />);
    rerender(<AnimatedCount value={101} />);
    expect(await screen.findByText("101")).toBeInTheDocument();
  });
});
