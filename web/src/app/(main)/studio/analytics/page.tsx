"use client";
import * as React from "react";
import dynamic from "next/dynamic";
import { Card, CardBody, StatItem, SegmentedControl, SectionHeader, GateNote, Skeleton } from "@/components/ui";
import { ANALYTICS_SERIES, won } from "@/lib/studio-mock";

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
 * Studio 애널리틱스 — Figma Web-StudioAnalytics(190:277) / W3.
 * 무의존 인라인 SVG 차트(라인=구독자 / 바=수익, chart-1~3 토큰) + 기간 세그먼트.
 * ※시계열 수치는 placeholder(실 데이터 B2 게이트).
 */
export default function StudioAnalyticsPage() {
  const [period, setPeriod] = React.useState("6m");
  const months = PERIODS.find((p) => p.value === period)?.months ?? 6;
  const series = ANALYTICS_SERIES.slice(-months);

  const last = series[series.length - 1];
  const first = series[0];
  // ANALYTICS_SERIES는 항상 비지 않은 정적 mock 배열이라 실질적으로 발생하지 않는 방어 가드.
  if (!last || !first) return null;
  const subDelta = last.subscribers - first.subscribers;
  const revDelta = last.revenue - first.revenue;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-headline text-on-surface">애널리틱스</h1>
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
