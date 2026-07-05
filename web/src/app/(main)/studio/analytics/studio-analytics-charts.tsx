import type { AnalyticsPoint } from "@/lib/studio-mock";

/**
 * Studio 애널리틱스 차트(R5-W3 #7b) — analytics/page.tsx에서 분리해 next/dynamic으로 지연 로드.
 * 무의존 인라인 SVG(라인/바) + x축 라벨. 값 범위를 뷰박스에 정규화(외부 차트 라이브러리 없음).
 */
const W = 320;
const H = 120;
const PAD = 8;

/** 라인 차트 — 무의존 SVG. 값 범위를 뷰박스에 정규화. */
export function LineChart({
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
export function BarChart({
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
