import { Skeleton } from "@/components/ui";

/**
 * (main) 세그먼트 로딩 — 셸(Sidebar/TopBar/BottomNav) 유지, 페이지 영역만 스켈레톤.
 * 피드/그리드 형태를 근사해 레이아웃 시프트를 줄인다.
 */
export default function MainLoading() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8" aria-busy="true">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="flex flex-col gap-2">
            <Skeleton className="aspect-square w-full rounded-lg" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    </div>
  );
}
