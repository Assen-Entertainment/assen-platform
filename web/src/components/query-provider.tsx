"use client";
import * as React from "react";
import { QueryClient, QueryClientProvider, MutationCache } from "@tanstack/react-query";
import { ApiError } from "@/lib/api/client";
import { emitUnauthorized } from "@/lib/api/session-events";

/** React Query Provider — 클라이언트 서버상태(캐싱·뮤테이션). 루트 레이아웃에서 children 래핑. */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: false } },
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
