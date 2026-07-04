import * as React from "react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// --- 모킹: config.wsUrl / 세션 유저 / 토스트를 테스트별로 제어 -----------------------
// config는 게터로 노출해 테스트마다 wsUrl을 갈아끼운다. session/useToast는 얇게 대체.
const { mockState, toastSpy } = vi.hoisted(() => ({
  mockState: { wsUrl: "", userId: "u1" as string | null },
  toastSpy: vi.fn(),
}));

vi.mock("@/lib/config", () => ({
  config: {
    get wsUrl() {
      return mockState.wsUrl;
    },
    apiUrl: "",
    siteUrl: "http://localhost:3000",
    env: "test",
  },
}));

vi.mock("@/lib/session", () => ({
  useSession: () => ({ user: mockState.userId ? { id: mockState.userId } : null }),
}));

vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({ toast: toastSpy }),
}));

import { useNotificationSocket } from "./use-notification-socket";
import { qk } from "@/lib/api/queries";

// --- mock WebSocket — jsdom 미구현이라 전역 대체. 인스턴스를 수집해 메시지/종료를 주입한다. ---
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  readyState = 0;
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: ((ev: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn(() => {
    this.readyState = 3;
  });
  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }
  emitOpen() {
    this.readyState = 1;
    this.onopen?.();
  }
  emitMessage(data: unknown) {
    this.onmessage?.({ data: typeof data === "string" ? data : JSON.stringify(data) });
  }
  emitClose(code = 1006) {
    this.readyState = 3;
    this.onclose?.({ code });
  }
}

const latest = () => MockWebSocket.instances[MockWebSocket.instances.length - 1];

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { qc, Wrapper };
}

beforeEach(() => {
  mockState.wsUrl = "";
  mockState.userId = "u1";
  toastSpy.mockClear();
  MockWebSocket.instances = [];
  vi.stubGlobal("WebSocket", MockWebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("useNotificationSocket (게이트·no-op)", () => {
  it("wsUrl 미설정이면 소켓을 만들지 않고 0을 반환한다(회귀 0)", () => {
    mockState.wsUrl = "";
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useNotificationSocket(), { wrapper: Wrapper });
    expect(MockWebSocket.instances).toHaveLength(0);
    expect(result.current).toBe(0);
  });

  it("비로그인이면 wsUrl이 있어도 연결하지 않는다", () => {
    mockState.wsUrl = "ws://test/ws/notifications";
    mockState.userId = null;
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useNotificationSocket(), { wrapper: Wrapper });
    expect(MockWebSocket.instances).toHaveLength(0);
    expect(result.current).toBe(0);
  });

  it("wsUrl+로그인 시 단 하나의 소켓을 연결한다(중복 방지)", () => {
    mockState.wsUrl = "ws://test/ws/notifications";
    const { Wrapper } = makeWrapper();
    renderHook(() => useNotificationSocket(), { wrapper: Wrapper });
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(latest().url).toBe("ws://test/ws/notifications");
  });
});

describe("useNotificationSocket (메시지 처리)", () => {
  it("unread_count 메시지로 뱃지 카운트를 동기화한다", () => {
    mockState.wsUrl = "ws://test/ws/notifications";
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useNotificationSocket(), { wrapper: Wrapper });
    act(() => {
      latest().emitMessage({ type: "unread_count", count: 5 });
    });
    expect(result.current).toBe(5);
  });

  it("notification 메시지로 뱃지 +1, 목록 무효화, 토스트를 발행한다", () => {
    mockState.wsUrl = "ws://test/ws/notifications";
    const { qc, Wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");
    const { result } = renderHook(() => useNotificationSocket(), { wrapper: Wrapper });
    act(() => {
      latest().emitMessage({
        type: "notification",
        notification: { id: "n1", kind: "like", title: "새 좋아요", href: "/post/1", created_at: "2026-07-04T00:00:00Z" },
      });
    });
    expect(result.current).toBe(1);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: qk.notifications });
    expect(toastSpy).toHaveBeenCalledWith({ title: "새 좋아요" });
  });

  it("파싱 불가/알 수 없는 메시지는 무시한다", () => {
    mockState.wsUrl = "ws://test/ws/notifications";
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useNotificationSocket(), { wrapper: Wrapper });
    act(() => {
      latest().emitMessage("not-json");
      latest().emitMessage({ type: "unknown" });
    });
    expect(result.current).toBe(0);
    expect(toastSpy).not.toHaveBeenCalled();
  });
});

describe("useNotificationSocket (재연결·정리)", () => {
  it("예기치 않은 종료(1006) 시 지수 백오프로 재연결한다", () => {
    vi.useFakeTimers();
    mockState.wsUrl = "ws://test/ws/notifications";
    const { Wrapper } = makeWrapper();
    renderHook(() => useNotificationSocket(), { wrapper: Wrapper });
    expect(MockWebSocket.instances).toHaveLength(1);
    act(() => {
      latest().emitClose(1006);
    });
    // 첫 재연결 지연 = 1000ms.
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(MockWebSocket.instances).toHaveLength(2);
  });

  it("close 4401(인증 만료)이면 재연결하지 않는다(세션 가드가 처리)", () => {
    vi.useFakeTimers();
    mockState.wsUrl = "ws://test/ws/notifications";
    const { Wrapper } = makeWrapper();
    renderHook(() => useNotificationSocket(), { wrapper: Wrapper });
    act(() => {
      latest().emitClose(4401);
    });
    act(() => {
      vi.advanceTimersByTime(60_000);
    });
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it("언마운트 시 소켓을 닫는다(누수 방지)", () => {
    mockState.wsUrl = "ws://test/ws/notifications";
    const { Wrapper } = makeWrapper();
    const { unmount } = renderHook(() => useNotificationSocket(), { wrapper: Wrapper });
    const ws = latest();
    unmount();
    expect(ws.close).toHaveBeenCalled();
  });
});
