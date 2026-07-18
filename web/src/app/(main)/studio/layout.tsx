"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/session";

/**
 * 스튜디오 게이트(blindspot 수정) — 크리에이터만 접근 가능.
 *
 * 기존엔 layout이 없어 /studio 이하 전 페이지(대시보드·상품·멤버십·정산·포스트)가
 * 비크리에이터에게도 그대로 노출됐다(통계 집계만 서버에서 막힘). 이 layout이 하위
 * 전체를 감싸 실 API 모드에서 세션 복원 후 비크리에이터면 "크리에이터 되기"로 유도하고,
 * 확정 전(복원 중·비크리에이터)에는 스튜디오 UI를 렌더하지 않아 노출 자체를 차단한다.
 *
 * ※mock/오프라인(useApi=false) 데모에서는 실 데이터가 없으므로 기존대로 열어 둔다.
 * ※미로그인은 미들웨어가 /login으로 먼저 리다이렉트한다(여기선 null 유지).
 */
export default function StudioLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, mounted, useApi } = useSession();
  const blocked = useApi && (!mounted || !user || !user.isCreator);

  React.useEffect(() => {
    if (useApi && mounted && user && !user.isCreator) router.replace("/become-creator");
  }, [useApi, mounted, user, router]);

  if (blocked) return null;
  return <>{children}</>;
}
