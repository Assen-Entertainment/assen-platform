"use client";
import * as React from "react";

/**
 * usePrefersReducedMotion — prefers-reduced-motion 사용자 여부(마운트 후 판정 — SSR 안전).
 * matchMedia 미지원 환경(구브라우저·테스트)은 false. 자동 스크롤 로드의 억제 판단에 사용.
 */
function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = () => setReduced(mq.matches);
    // addEventListener 미지원(구 Safari)은 addListener 폴백.
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, []);
  return reduced;
}

export interface UseInfiniteScrollOptions {
  /** sentinel이 뷰포트에 근접하면 호출(보통 fetchNextPage). */
  onLoadMore: () => void;
  /** 자동 로드 활성 조건(예: hasNextPage && !isFetchingNextPage). false면 관찰 중단. */
  enabled: boolean;
  /** 뷰포트 근접 여유(px) — 하단 도달 전에 미리 로드. 기본 400. */
  rootMargin?: number;
}

/**
 * useInfiniteScroll — sentinel ref가 뷰포트에 근접하면 onLoadMore를 자동 호출(무한 스크롤).
 *
 * 접근성·회귀 안전:
 *  • prefers-reduced-motion 사용자·IntersectionObserver 미지원 환경엔 옵저버를 붙이지 않는다
 *    → "더 불러오기" 버튼 폴백만 동작(자동 로드 없음). 뷰는 버튼을 항상 유지하므로 회귀 0.
 *  • enabled가 false면(로딩 중·다음 페이지 없음) 관찰을 끊어 중복 호출을 막고, 로딩이 끝나
 *    다시 true가 되면 sentinel이 여전히 보일 때만 재관찰해 다음 페이지를 이어 로드한다.
 */
export function useInfiniteScroll(
  ref: React.RefObject<Element | null>,
  { onLoadMore, enabled, rootMargin = 400 }: UseInfiniteScrollOptions,
): void {
  const reduced = usePrefersReducedMotion();
  // 최신 콜백을 ref로 고정 — 옵저버를 재생성하지 않고 최신 클로저를 호출.
  const onLoadMoreRef = React.useRef(onLoadMore);
  onLoadMoreRef.current = onLoadMore;

  React.useEffect(() => {
    const el = ref.current;
    if (!el || !enabled || reduced) return;
    if (typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) onLoadMoreRef.current();
      },
      { rootMargin: `${rootMargin}px` },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ref, enabled, reduced, rootMargin]);
}
