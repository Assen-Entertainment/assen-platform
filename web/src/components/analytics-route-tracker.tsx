"use client";
import * as React from "react";
import { usePathname } from "next/navigation";
import { initAnalytics, track } from "@/lib/analytics";

/**
 * 분석 라우트 트래커 — page_view 이벤트의 **단일** 발화 지점(중복 방지).
 * 마운트 시 기본 수집기 초기화(initAnalytics) 후, 경로(pathname) 변경마다 page_view를 발화한다.
 * 쿼리스트링은 담지 않는다(검색어 등 PII 유입 차단 — 경로만). 렌더 출력 없음. 루트 레이아웃에 1회 마운트.
 */
export function AnalyticsRouteTracker() {
  const pathname = usePathname();

  // 기본 수집기 등록(멱등·클라 전용) — 첫 page_view 이전에 실행되도록 먼저 선언.
  React.useEffect(() => {
    initAnalytics();
  }, []);

  // 경로 변경마다 page_view 1회(초기 마운트 포함).
  React.useEffect(() => {
    track("page_view", { path: pathname });
  }, [pathname]);

  return null;
}
