"use client";
import * as React from "react";
import { Card, CardBody, StatItem, SegmentedControl, SectionHeader } from "@/components/ui";
import { ANALYTICS_SERIES, won, type AnalyticsPoint } from "@/lib/studio-mock";

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
      <p className="text-center text-caption text-on-surface-variant">※ 데모 — 시계열 수치는 placeholder(실 데이터 게이트)</p>
    </div>
  );
}

const W = 320;
const H = 120;
const PAD = 8;

/** 라인 차트 — 무의존 SVG. 값 범위를 뷰박스에 정규화. */
function LineChart({
  series,
  accessor,
  color,
  ariaLabel,
}: {
  series: AnalyticsPoint[];
  accessor: (p: AnalyticsPoint) => number;
  color: string;
  ariaLabel: string;
}) {
  const values = series.map(accessor);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const stepX = series.length > 1 ? (W - PAD * 2) / (series.length - 1) : 0;
  const points = values.map((v, i) => {
    const x = PAD + i * stepX;
    const y = PAD + (1 - (v - min) / span) * (H - PAD * 2);
    return { x, y };
  });
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

  return (
    <figure className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel} className="w-full">
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--color-chart-grid)" strokeWidth={1} />
        <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
        {points.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={2.5} fill={color} />
        ))}
      </svg>
      <ChartAxis series={series} />
    </figure>
  );
}

/** 바 차트 — 무의존 SVG. */
function BarChart({
  series,
  accessor,
  color,
  ariaLabel,
}: {
  series: AnalyticsPoint[];
  accessor: (p: AnalyticsPoint) => number;
  color: string;
  ariaLabel: string;
}) {
  const values = series.map(accessor);
  const max = Math.max(...values) || 1;
  const slot = (W - PAD * 2) / series.length;
  const barW = slot * 0.5;

  return (
    <figure className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel} className="w-full">
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--color-chart-grid)" strokeWidth={1} />
        {values.map((v, i) => {
          const h = (v / max) * (H - PAD * 2);
          const x = PAD + i * slot + (slot - barW) / 2;
          const y = H - PAD - h;
          return <rect key={i} x={x} y={y} width={barW} height={h} rx={2} fill={color} />;
        })}
      </svg>
      <ChartAxis series={series} />
    </figure>
  );
}

/** x축 라벨(월). */
function ChartAxis({ series }: { series: AnalyticsPoint[] }) {
  return (
    <div className="flex justify-between px-1 text-caption text-on-surface-variant">
      {series.map((p) => (
        <span key={p.label}>{p.label}</span>
      ))}
    </div>
  );
}
