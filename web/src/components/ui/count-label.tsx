import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * CountLabel — Figma DS(59:6). 카운트 + 라벨(예: "12.4k 팔로워"). tabular-nums 정렬.
 */
export interface CountLabelProps extends React.HTMLAttributes<HTMLSpanElement> {
  count: number;
  label?: string;
  /** 1000 단위 축약(12.4k). 기본 false. */
  compact?: boolean;
}

function fmt(n: number, compact?: boolean): string {
  if (compact && n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, "") + "k";
  return n.toLocaleString("ko-KR");
}

export function CountLabel({ count, label, compact, className, ...props }: CountLabelProps) {
  return (
    <span className={cn("inline-flex items-baseline gap-1 text-body-s text-on-surface-variant", className)} {...props}>
      <span className="font-medium tabular-nums text-on-surface">{fmt(count, compact)}</span>
      {label ? <span>{label}</span> : null}
    </span>
  );
}
