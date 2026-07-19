"use client";
import * as React from "react";

/**
 * usePrefersReducedMotion — OS의 prefers-reduced-motion 설정을 구독한다.
 * SSR/첫 렌더에서는 false(모션 허용)를 반환하고, 마운트 후 실제 값으로 동기화한다.
 * jsdom 등 matchMedia 미구현 환경에서도 안전(false 폴백).
 *
 * CSS 애니메이션은 globals.css의 전역 @media 가드가 처리하지만, 연결 글로우처럼
 * "reduced 에서 다른 표현(정적 틴트)"이 필요한 JS 분기용으로 이 훅을 쓴다.
 */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = React.useState(false);

  React.useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    // Safari<14는 addEventListener 미지원 → addListener 폴백.
    if (typeof mq.addEventListener === "function") {
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    }
    mq.addListener(onChange);
    return () => mq.removeListener(onChange);
  }, []);

  return reduced;
}
