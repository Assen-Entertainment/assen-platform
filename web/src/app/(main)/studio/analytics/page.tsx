"use client";
import * as React from "react";
import dynamic from "next/dynamic";
import { Card, CardBody, StatItem, SegmentedControl, SectionHeader, GateNote, Skeleton, EmptyState } from "@/components/ui";
import { won } from "@/lib/studio-mock";
import { getAnalyticsDemoSeries, type AnalyticsPoint } from "@/lib/api";

// 차트 코드 스플리팅(R5-W3 #7b) — 무의존 SVG 차트를 별 청크로 지연 로드(초기 번들에서 분리).
// 로딩 중엔 동일 높이 스켈레톤으로 레이아웃 시프트 방지.
const ChartSkeleton = () => <Skeleton className="h-[120px] w-full" />;
const LineChart = dynamic(() => import("./studio-analytics-charts").then((m) => m.LineChart), {
  loading: ChartSkeleton,
});
const BarChart = dynamic(() => import("./studio-analytics-charts").then((m) => m.BarChart), {
  loading: ChartSkeleton,
});

const PERIODS: { label: string; value: string; months: number }[] = [
  { label: "3개월", value: "3m", months: 3 },
  { label: "6개월", value: "6m", months: 6 },
];

/**
 * Studio 애널리틱스 — 오너 스코프 라우트(/studio/* 는 middleware 세션 가드). getAnalyticsDemoSeries는
 * 라이브(USE_API)에서 null(서버 수익/구독자 시계열 계약 없음)을, mock 폴백에서만 데모 시계열을
 * 반환한다. 라이브에선 날조 수치 대신 "준비 중" 안내를 렌더하고, 그 mock 데이터는 lib/api에서
 * 트리셰이킹되어 번들에 실리지 않는다(ASS-289 #5).
 */
export default function StudioAnalyticsPage() {
  const series = getAnalyticsDemoSeries();
  // 라이브: 시계열 없음 → "준비 중"(mock 수치 렌더 안 함). 빈 배열(스텁)도 동일 처리.
  if (!series || series.length === 0) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col gap-5">
        <h1 className="text-headline text-on-surface">애널리틱스</h1>
        <div className="rounded-lg border border-outline bg-surface p-4">
          <EmptyState
            title="애널리틱스 데이터 준비 중이에요"
            description="구독자·수익 추이는 준비되는 대로 이곳에 표시됩니다. 아직 표시할 데이터가 없어요."
          />
        </div>
      </div>
    );
  }
  return <MockAnalytics all={series} />;
}

/**
 * Studio 애널리틱스 데모(mock 전용) — Figma Web-StudioAnalytics(190:277) / W3.
 * 무의존 인라인 SVG 차트(라인=구독자 / 바=수익, chart-1~3 토큰) + 기간 세그먼트.
 * ※시계열 수치는 placeholder(실 데이터 게이트). 데모 데이터로 명시 라벨한다.
 */
function MockAnalytics({ all }: { all: AnalyticsPoint[] }) {
  const [period, setPeriod] = React.useState("6m");
  const months = PERIODS.find((p) => p.value === period)?.months ?? 6;
  const series = all.slice(-months);

  const last = series[series.length - 1];
  const first = series[0];
  // all은 mock 경로에서 항상 비지 않은 배열이라 실질적으로 발생하지 않는 방어 가드.
  if (!last || !first) return null;
  const subDelta = last.subscribers - first.subscribers;
  const revDelta = last.revenue - first.revenue;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 flex-col">
          <h1 className="text-headline text-on-surface">애널리틱스</h1>
          <span className="text-caption text-on-surface-variant">데모 데이터 — 실 수치가 아니에요</span>
        </div>
        <SegmentedControl
          options={PERIODS.map((p) => ({ label: p.label, value: p.value }))}
          value={period}
          onValueChange={setPeriod}
        />
      </div>

      <div className="grid grid-cols-2 gap-4 rounded-lg border border-outline bg-surface p-4">
        <StatItem
          label="구독자"
          value={last.subscribers.toLocaleString("ko-KR")}
          delta={`${subDelta >= 0 ? "+" : ""}${subDelta.toLocaleString("ko-KR")}`}
          trend={subDelta >= 0 ? "up" : "down"}
        />
        <StatItem
          label="월 수익"
          value={won(last.revenue)}
          delta={`${revDelta >= 0 ? "+" : ""}${won(revDelta)}`}
          trend={revDelta >= 0 ? "up" : "down"}
        />
      </div>

      <Card>
        <CardBody className="gap-3">
          <SectionHeader as="h3" title="구독자 추이" description="기간 내 구독자 수 변화" />
          <LineChart series={series} accessor={(p) => p.subscribers} color="var(--color-chart-1)" ariaLabel="구독자 추이 라인 차트" />
        </CardBody>
      </Card>

      <Card>
        <CardBody className="gap-3">
          <SectionHeader as="h3" title="월 수익" description="기간 내 월별 수익" />
          <BarChart series={series} accessor={(p) => p.revenue} color="var(--color-chart-2)" ariaLabel="월 수익 바 차트" />
        </CardBody>
      </Card>
      <GateNote as="p" className="text-center text-caption text-on-surface-variant">※ 데모 — 시계열 수치는 placeholder(실 데이터 게이트)</GateNote>
    </div>
  );
}
