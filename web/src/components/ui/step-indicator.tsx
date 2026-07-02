import * as React from "react";
import { cn } from "@/lib/utils";

/** StepIndicator — 온보딩/체크아웃 단계 표시. 완료=primary 채움, 현재=primary 보더. */
export interface StepIndicatorProps {
  steps: string[];
  current: number; // 0-based
  className?: string;
}

export function StepIndicator({ steps, current, className }: StepIndicatorProps) {
  return (
    <ol className={cn("flex items-center", className)}>
      {steps.map((s, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={s} className="flex items-center">
            <span
              className={cn(
                "flex size-7 shrink-0 items-center justify-center rounded-full text-caption font-medium",
                done
                  ? "bg-primary text-on-primary"
                  : active
                    ? "border-2 border-primary text-primary"
                    : "bg-surface-container-high text-on-surface-variant",
              )}
            >
              {done ? "✓" : i + 1}
            </span>
            <span className={cn("ml-2 text-label", active ? "text-on-surface" : "text-on-surface-variant")}>{s}</span>
            {i < steps.length - 1 && <span className="mx-3 h-px w-8 bg-outline" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}
