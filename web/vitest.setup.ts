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
