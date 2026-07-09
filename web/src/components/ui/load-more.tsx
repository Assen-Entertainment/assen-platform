"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "./button";
import { Spinner } from "./spinner";
import { useInfiniteScroll } from "@/lib/use-infinite-scroll";

export interface LoadMoreProps {
  /** 다음 페이지 존재 여부 — false면 아무것도 렌더하지 않음. */
  hasNextPage: boolean;
  /** 다음 페이지 로딩 중 여부(버튼 disabled + 스피너 노출). */
  isFetchingNextPage: boolean;
  /** 다음 페이지 로드 트리거(보통 fetchNextPage). */
  onLoadMore: () => void;
  /** 현재 로드된 총 아이템 수 — 증가분을 aria-live로 안내하는 데 쓴다("n개 더 불러왔어요"). */
  itemCount: number;
  /** sentinel(IntersectionObserver) 기반 자동 로드 활성화 — 기본 true. false면 버튼 폴백만. */
  auto?: boolean;
  /** 대기 상태 버튼 라벨. */
  label?: string;
  /** 로딩 중 버튼 라벨. */
  loadingLabel?: string;
  className?: string;
}

/**
 * LoadMore — 무한 스크롤 sentinel + "더 보기" 버튼 폴백을 한 번에 제공하는 공용 프리미티브.
 * 7개 뷰(피드/디스커버리/주문/알림/스토어/검색/포스트상세)에 복제되어 있던 블록을 통합했다.
 * 추가 로드가 끝나면 `aria-live="polite"` 리전으로 "n개 더 불러왔어요"를 스크린리더에 안내한다
 * (기존 무한스크롤 append는 SR에 무고지였다 — 다음 페이지가 조용히 DOM에 붙기만 했음).
 */
export function LoadMore({
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
  itemCount,
  auto = true,
  label = "더 보기",
  loadingLabel = "불러오는 중…",
  className,
}: LoadMoreProps) {
  const sentinelRef = React.useRef<HTMLDivElement>(null);
  const canLoadMore = hasNextPage && !isFetchingNextPage;
  useInfiniteScroll(sentinelRef, {
    enabled: auto && canLoadMore,
    onLoadMore: () => {
      if (canLoadMore) onLoadMore();
    },
  });

  // itemCount 증가분을 감지해 안내 문구를 갱신(최초 마운트는 무음 — 증가분이 없으므로).
  const [announce, setAnnounce] = React.useState("");
  const prevCount = React.useRef(itemCount);
  React.useEffect(() => {
    const delta = itemCount - prevCount.current;
    if (delta > 0) setAnnounce(`${delta}개 더 불러왔어요`);
    prevCount.current = itemCount;
  }, [itemCount]);

  if (!hasNextPage) return null;

  return (
    <div className={cn("flex flex-col items-center gap-3", className)}>
      {auto ? <div ref={sentinelRef} aria-hidden className="h-px w-full" /> : null}
      {isFetchingNextPage ? <Spinner aria-label="더 불러오는 중" /> : null}
      <Button variant="outline" onClick={onLoadMore} disabled={isFetchingNextPage}>
        {isFetchingNextPage ? loadingLabel : label}
      </Button>
      <span role="status" aria-live="polite" className="sr-only">
        {announce}
      </span>
    </div>
  );
}
