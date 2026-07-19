import { describe, it, expect, vi, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { ConnectionGlow } from "./connection-glow";

afterEach(() => {
  vi.useRealTimers();
});

describe("ConnectionGlow — 브랜드 시그니처 프리미티브", () => {
  it("show=false면 아무것도 렌더하지 않는다", () => {
    const { container } = render(<ConnectionGlow show={false} depth="follow" />);
    expect(container.querySelector("[data-connection-glow]")).toBeNull();
  });

  it("show=true면 깊이 태그를 가진 장식 글로우를 렌더한다(aria-hidden)", () => {
    const { container } = render(<ConnectionGlow show depth="subscribe" />);
    const glow = container.querySelector("[data-connection-glow='subscribe']");
    expect(glow).not.toBeNull();
    expect(glow).toHaveAttribute("aria-hidden");
    // 장식이므로 포인터 이벤트를 가로채지 않는다.
    expect(glow?.className).toContain("pointer-events-none");
  });

  it("깊이 지속시간 후 onDone을 한 번 호출한다(one-shot)", () => {
    vi.useFakeTimers();
    const onDone = vi.fn();
    render(<ConnectionGlow show depth="support" onDone={onDone} />);
    expect(onDone).not.toHaveBeenCalled();
    vi.advanceTimersByTime(900); // support = 860ms
    expect(onDone).toHaveBeenCalledTimes(1);
  });
});
