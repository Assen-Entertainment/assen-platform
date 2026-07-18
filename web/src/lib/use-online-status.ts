"use client";
import * as React from "react";
import { onlineManager } from "@tanstack/react-query";

/**
 * 온라인 상태 구독 — React Query `onlineManager`(내부적으로 navigator.onLine + window online/offline 이벤트)를
 * 단일 소스로 사용한다. useSyncExternalStore로 SSR 안전(서버 스냅샷=온라인 가정 → 하이드레이션 불일치 없음).
 * onlineManager는 복귀 시 paused 뮤테이션 재개 + refetchOnReconnect(기본 true)로 쿼리 재시도를 자동 처리한다.
 */
export function useOnlineStatus(): boolean {
  return React.useSyncExternalStore(
    (onChange) => onlineManager.subscribe(onChange),
    () => onlineManager.isOnline(),
    () => true, // SSR: 온라인으로 가정
  );
}
