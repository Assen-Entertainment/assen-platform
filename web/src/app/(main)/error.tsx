"use client";
import { useEffect } from "react";
import { ErrorState } from "@/components/ui";

/**
 * (main) 세그먼트 에러 경계 — 셸(Sidebar/TopBar/BottomNav)을 유지한 채 페이지 영역만
 * 에러 표시. reset()으로 세그먼트 재렌더(재시도).
 */
export default function MainError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <ErrorState
        title="문제가 발생했어요"
        description="잠시 후 다시 시도해 주세요. 계속되면 문의해 주세요."
        onRetry={reset}
      />
    </div>
  );
}
