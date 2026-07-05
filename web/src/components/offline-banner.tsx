"use client";
import * as React from "react";
import { useOnlineStatus } from "@/lib/use-online-status";

/**
 * OfflineBanner — 오프라인 감지 상단 배너. 셸에 1회 마운트.
 * 오프라인이면 안내를 노출하고, 복귀 시 자동 해제(onlineManager가 refetch/뮤테이션 재개까지 처리).
 * SSR 안전(useOnlineStatus 서버 스냅샷=온라인 → 초기 렌더는 null).
 */
export function OfflineBanner() {
  const online = useOnlineStatus();
  if (online) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center justify-center gap-2 bg-warning-container px-4 py-2 text-body-s text-on-warning-container"
    >
      오프라인 상태예요 — 연결되면 자동으로 다시 시도해요
    </div>
  );
}
