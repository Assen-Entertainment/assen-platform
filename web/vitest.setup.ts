import "@testing-library/jest-dom/vitest";

// jsdom은 matchMedia 미구현 → ThemeProvider(prefers-color-scheme) 사용 시 필요. 기본 light(matches:false).
if (typeof window !== "undefined" && !window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
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

// jsdom은 IntersectionObserver 미구현 → framer-motion whileInView(스크롤 리빌) 사용 시 필요.
// observe() 즉시 교차 통지 → 모션 요소가 최종(가시) 상태로 진입해 테스트 렌더가 안정된다.
// writable=true라 개별 테스트(use-infinite-scroll 등)가 자체 mock으로 재할당 가능(회귀 0).
if (typeof globalThis.IntersectionObserver === "undefined") {
  class MockIntersectionObserver implements IntersectionObserver {
    readonly root: Element | Document | null = null;
    readonly rootMargin: string = "";
    readonly thresholds: ReadonlyArray<number> = [];
    private cb: IntersectionObserverCallback;
    constructor(cb: IntersectionObserverCallback) {
      this.cb = cb;
    }
    observe(target: Element): void {
      this.cb([{ isIntersecting: true, target } as IntersectionObserverEntry], this);
    }
    unobserve(): void {}
    disconnect(): void {}
    takeRecords(): IntersectionObserverEntry[] {
      return [];
    }
  }
  Object.defineProperty(globalThis, "IntersectionObserver", {
    writable: true,
    configurable: true,
    value: MockIntersectionObserver,
  });
  if (typeof window !== "undefined") {
    Object.defineProperty(window, "IntersectionObserver", {
      writable: true,
      configurable: true,
      value: MockIntersectionObserver,
    });
  }
}
