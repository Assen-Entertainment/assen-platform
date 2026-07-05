"use client";
import Link from "next/link";
import { StatItem, Skeleton, EmptyState, Button } from "@/components/ui";
import { useStudioStats } from "@/lib/api/queries";
import type { StudioStats } from "@/lib/api";

/**
 * 대시보드 카드 정의 — 라벨 + StudioStats에서 뽑을 카운트 필드.
 * ※금액(수익) 카드는 없다 — 서버 계약(StudioStatsOut)에 수익 없음(정산 게이트 ASS-229).
 *   금액은 정산 페이지(아래 바로가기)에서만 다룬다.
 */
const STAT_CARDS: { label: string; field: keyof StudioStats }[] = [
  { label: "팔로워", field: "followers" },
  { label: "포스트", field: "posts" },
  { label: "구독자", field: "subscribers" },
  { label: "주문", field: "orders" },
];

const GRID_CLASS = "grid grid-cols-2 gap-4 rounded-lg border border-outline bg-surface p-4 lg:grid-cols-4";

/**
 * 스튜디오 대시보드 통계 그리드(R4-W5) — 서버 GET /studio/stats 실 카운트를 소비한다.
 * 로딩=스켈레톤 / null(비크리에이터·비로그인)=안내 / 성공=실 카운트 StatItem.
 * ★수익 카드 없음: 서버 계약에 금액이 없어 절대 날조하지 않는다(증감률 delta도 표기하지 않음).
 */
export function StudioStatsGrid() {
  const { data, isLoading } = useStudioStats();

  // 로딩 — StatItem 레이아웃(라벨+수치)에 맞춘 스켈레톤 4칸.
  if (isLoading) {
    return (
      <div className={GRID_CLASS} aria-busy>
        {STAT_CARDS.map((c) => (
          <div key={c.field} className="flex flex-col gap-1">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-8 w-20" />
          </div>
        ))}
      </div>
    );
  }

  // 방어적 — 통계 없음(403 비크리에이터/401 비로그인). 카운트를 0으로 날조하지 않고 안내한다.
  if (!data) {
    return (
      <div className="rounded-lg border border-outline bg-surface p-4">
        <EmptyState
          title="통계를 불러올 수 없어요"
          description="크리에이터 스튜디오 통계는 크리에이터 계정에서 확인할 수 있어요."
          action={
            <Button asChild variant="outline">
              <Link href="/studio/settlement">정산 내역 보기</Link>
            </Button>
          }
        />
      </div>
    );
  }

  // 실 카운트 — 전부 정수(금액 아님). ko-KR 천단위 포맷.
  return (
    <div className={GRID_CLASS}>
      {STAT_CARDS.map((c) => (
        <StatItem key={c.field} label={c.label} value={data[c.field].toLocaleString("ko-KR")} />
      ))}
    </div>
  );
}
