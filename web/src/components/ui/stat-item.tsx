import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * StatItem — Figma DS StatItem(116:17). 스튜디오 대시보드/정산 요약 지표.
 * label(상단 캡션) + value(강조 수치) + 선택적 delta(증감, trend로 색 결정).
 */
export interface StatItemProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: string;
  delta?: string;
  trend?: "up" | "down" | "flat";
  /** placeholder 수치임을 알리는 각주(정산 수수료 등 단독 확정 금지 항목). */
  note?: string;
}

export const StatItem = React.forwardRef<HTMLDivElement, StatItemProps>(
  ({ label, value, delta, trend = "flat", note, className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-1", className)} {...props}>
      <span className="text-body-s text-on-surface-variant">{label}</span>
      <span className="text-display-m tabular-nums text-on-surface">{value}</span>
      {delta ? (
        <span
          className={cn(
            "text-caption tabular-nums",
            trend === "up" ? "text-success" : trend === "down" ? "text-error" : "text-on-surface-variant",
          )}
        >
          {delta}
        </span>
      ) : null}
      {note ? <span className="text-caption text-on-surface-variant">{note}</span> : null}
    </div>
  ),
);
StatItem.displayName = "StatItem";
