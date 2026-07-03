import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * TimeLabel — Figma DS(59:4). 시각 라벨(상대/절대). <time> 시맨틱 + dateTime 속성.
 */
export interface TimeLabelProps extends React.TimeHTMLAttributes<HTMLTimeElement> {
  children: React.ReactNode;
  /** ISO datetime(옵션). */
  dateTime?: string;
}

export function TimeLabel({ children, dateTime, className, ...props }: TimeLabelProps) {
  return (
    <time dateTime={dateTime} className={cn("text-caption text-on-surface-variant", className)} {...props}>
      {children}
    </time>
  );
}
