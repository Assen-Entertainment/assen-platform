import * as React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useInfiniteScroll } from "./use-infinite-scroll";

/** IntersectionObserver mock — 관찰 콜백을 캡처해 교차를 수동 트리거(jsdom 미구현 대체). */
class MockIO {
  cb: IntersectionObserverCallback;
  elements = new Set<Element>();
  disconnected = false;
  constructor(cb: IntersectionObserverCallback) {
    this.cb = cb;
    ioInstances.push(this);
  }
  observe(el: Element) {
    this.elements.add(el);
  }
  unobserve(el: Element) {
    this.elements.delete(el);
  }
  disconnect() {
    this.disconnected = true;
    this.elements.clear();
  }
  /** 테스트 헬퍼 — 교차 이벤트 시뮬(연결 해제된 옵저버는 발화하지 않음). */
  trigger(isIntersecting: boolean) {
    if (this.disconnected) return;
    this.cb([{ isIntersecting } as IntersectionObserverEntry], this as unknown as IntersectionObserver);
  }
}
let ioInstances: MockIO[] = [];
const active = () => ioInstances.filter((io) => !io.disconnected);

function setMatchMedia(reduced: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: reduced,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

beforeEach(() => {
  ioInstances = [];
  (globalThis as unknown as { IntersectionObserver: typeof MockIO }).IntersectionObserver = MockIO;
  setMatchMedia(false);
});
afterEach(() => vi.restoreAllMocks());

function renderScroll(enabled: boolean, onLoadMore: () => void) {
  const el = document.createElement("div");
  const ref = { current: el } as React.RefObject<HTMLDivElement>;
  const view = renderHook(({ en }) => useInfiniteScroll(ref, { enabled: en, onLoadMore }), {
    initialProps: { en: enabled },
  });
  return { ref, ...view };
}

describe("useInfiniteScroll", () => {
  it("enabled면 sentinel 교차 시 onLoadMore를 호출한다", () => {
    const onLoadMore = vi.fn();
    renderScroll(true, onLoadMore);
    expect(active()).toHaveLength(1);
    act(() => active()[0].trigger(true));
    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  it("교차하지 않으면(isIntersecting=false) 호출하지 않는다", () => {
    const onLoadMore = vi.fn();
    renderScroll(true, onLoadMore);
    act(() => active()[0].trigger(false));
    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it("enabled=false면 옵저버를 붙이지 않는다(버튼 폴백만)", () => {
    const onLoadMore = vi.fn();
    renderScroll(false, onLoadMore);
    expect(active()).toHaveLength(0);
  });

  it("enabled가 false→true로 바뀌면 관찰을 재개한다", () => {
    const onLoadMore = vi.fn();
    const { rerender } = renderScroll(false, onLoadMore);
    expect(active()).toHaveLength(0);
    act(() => rerender({ en: true }));
    expect(active()).toHaveLength(1);
    act(() => active()[0].trigger(true));
    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  it("prefers-reduced-motion 사용자에겐 옵저버를 붙이지 않는다(자동 로드 억제)", () => {
    setMatchMedia(true);
    const onLoadMore = vi.fn();
    renderScroll(true, onLoadMore);
    // 초기 렌더에서 잠시 붙더라도 reduced 감지 후 모두 연결 해제된다.
    expect(active()).toHaveLength(0);
  });
});
