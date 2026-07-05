import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDebouncedValue } from "./use-debounced-value";

describe("useDebouncedValue", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("delay 경과 후에만 값이 갱신된다", () => {
    const { result, rerender } = renderHook(({ v }) => useDebouncedValue(v, 250), {
      initialProps: { v: "a" },
    });
    expect(result.current).toBe("a");

    rerender({ v: "ab" });
    // 아직 delay 전 — 직전 값 유지.
    expect(result.current).toBe("a");
    act(() => vi.advanceTimersByTime(250));
    expect(result.current).toBe("ab");
  });

  it("delay 내 연속 입력은 마지막 값만 반영한다(중간 요청 억제)", () => {
    const { result, rerender } = renderHook(({ v }) => useDebouncedValue(v, 250), {
      initialProps: { v: "a" },
    });
    rerender({ v: "ab" });
    act(() => vi.advanceTimersByTime(100));
    rerender({ v: "abc" });
    act(() => vi.advanceTimersByTime(100));
    // 100+100 < 250 이고 매 입력이 타이머를 리셋 → 아직 초기값.
    expect(result.current).toBe("a");
    act(() => vi.advanceTimersByTime(250));
    expect(result.current).toBe("abc");
  });
});
