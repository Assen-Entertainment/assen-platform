"use client";
import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

/** React Query Provider — 클라이언트 서버상태(캐싱·뮤테이션). 루트 레이아웃에서 children 래핑. */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: false } } }),
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
