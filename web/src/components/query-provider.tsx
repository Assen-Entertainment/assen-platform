"use client";
import * as React from "react";
import { QueryClient, QueryClientProvider, MutationCache } from "@tanstack/react-query";
import { ApiError } from "@/lib/api/client";
import { emitUnauthorized } from "@/lib/api/session-events";

/**
 * 쿼리 재시도 정책 — 4xx(클라이언트 오류: 401/403/404 등)는 재요청해도 결과가 같으므로 즉시 포기.
 * 5xx·네트워크 오류(ApiError가 아닌 경우 포함)만 최대 2회 제한적으로 재시도(TanStack 기본 3회보다
 * 보수적). useStudioPosts의 국소 retry:false(403 무재시도)와 동일한 방침을 전역화한 것.
 */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < 2;
}

/** React Query Provider — 클라이언트 서버상태(캐싱·뮤테이션). 루트 레이아웃에서 children 래핑. */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            // staleTime(1분)보다 넉넉히 — 화면 전환으로 언마운트된 쿼리도 잠시 캐시에 남아
            // 재방문 시 즉시 표시(백그라운드 리페치와 병행). TanStack 기본값(5분)을 그대로 명시.
            gcTime: 5 * 60_000,
            refetchOnWindowFocus: false,
            retry: shouldRetry,
          },
        },
        // 뮤테이션 401은 세션 만료 → 전역 가드(SessionGuard)로 통지(토스트·로그인 유도).
        mutationCache: new MutationCache({
          onError: (error) => {
            if (error instanceof ApiError && error.status === 401) emitUnauthorized();
          },
        }),
      }),
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
