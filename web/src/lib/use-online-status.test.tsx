import { describe, it, expect, afterEach } from "vitest";
import { renderHook, render, screen, act } from "@testing-library/react";
import { onlineManager } from "@tanstack/react-query";
import { useOnlineStatus } from "@/lib/use-online-status";
import { OfflineBanner } from "@/components/offline-banner";

describe("useOnlineStatus / OfflineBanner (오프라인 감지)", () => {
  // 각 테스트 후 온라인으로 복원(전역 onlineManager 상태 누수 방지).
  afterEach(() => act(() => onlineManager.setOnline(true)));

  it("기본은 온라인(true)", () => {
    const { result } = renderHook(() => useOnlineStatus());
    expect(result.current).toBe(true);
  });

  it("오프라인 전환 시 false, 복귀 시 true", () => {
    const { result } = renderHook(() => useOnlineStatus());
    act(() => onlineManager.setOnline(false));
    expect(result.current).toBe(false);
    act(() => onlineManager.setOnline(true));
    expect(result.current).toBe(true);
  });

  it("배너: 온라인이면 미노출, 오프라인이면 안내를 노출한다", () => {
    render(<OfflineBanner />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    act(() => onlineManager.setOnline(false));
    expect(screen.getByRole("status")).toHaveTextContent("오프라인 상태예요");
    act(() => onlineManager.setOnline(true));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
