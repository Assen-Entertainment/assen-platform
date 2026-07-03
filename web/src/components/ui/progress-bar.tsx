import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * ProgressBar — Figma DS ProgressBar(52:3). 진행률 트랙+필. 목표 달성/업로드/티어 혜택 빌드업 등.
 * value/max 로 퍼센트 산출, role=progressbar(a11y). accent=크리에이터 액센트 색(스코프 필요).
 */
export interface ProgressBarProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  label?: string;
  accent?: boolean;
  /** 우측에 퍼센트/수치 라벨 노출. */
  showValue?: boolean;
}

export const ProgressBar = React.forwardRef<HTMLDivElement, ProgressBarProps>(
  ({ value, max = 100, label, accent, showValue, className, ...props }, ref) => {
    const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
    return (
      <div ref={ref} className={cn("flex flex-col gap-1", className)} {...props}>
        {label || showValue ? (
          <div className="flex items-center justify-between gap-2 text-caption text-on-surface-variant">
            {label ? <span>{label}</span> : <span />}
            {showValue ? <span className="tabular-nums">{Math.round(pct)}%</span> : null}
          </div>
        ) : null}
        <div
          role="progressbar"
          aria-valuenow={Math.round(pct)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={label}
          className="h-2 w-full overflow-hidden rounded-full bg-surface-container-high"
        >
          <div
            className={cn("h-full rounded-full transition-[width]", accent ? "bg-creator-accent" : "bg-primary")}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    );
  },
);
ProgressBar.displayName = "ProgressBar";
