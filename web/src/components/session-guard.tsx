"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/use-toast";
import { onUnauthorized } from "@/lib/api/session-events";

/**
 * 전역 401 가드 — 뮤테이션이 인증 실패(401)하면 토스트로 안내하고 로그인으로 유도한다.
 * (세션 read 401은 비로그인 정상 상태라 여기서 다루지 않는다 — index.ts에서 빈 목록 처리.)
 * 렌더 출력 없음. Toaster·라우터 컨텍스트 하위에 1회 마운트.
 */
export function SessionGuard() {
  const router = useRouter();
  const { toast } = useToast();
  React.useEffect(
    () =>
      onUnauthorized(() => {
        toast({ title: "로그인이 필요해요", description: "다시 로그인해 주세요." });
        router.push("/login");
      }),
    [router, toast],
  );
  return null;
}
