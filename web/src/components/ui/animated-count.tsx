"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion";

/**
 * AnimatedCount — "살아있는 숫자". 값이 바뀌면 이전값→새값으로 tabular 틱업 애니메이션한다
 * (팔로우 시 팔로워 카운트 등, 리추얼의 일부). 첫 렌더/reduced-motion에서는 애니 없이 즉시 표시.
 *
 * tabular-nums로 자릿수 폭이 고정되어 카운트가 오르내려도 레이아웃이 흔들리지 않는다(CLS 0).
 * requestAnimationFrame 기반(외부 의존 0) · easeOutCubic 감속.
 */
export interface AnimatedCountProps
  extends Omit<React.HTMLAttributes<HTMLSpanElement>, "children"> {
  value: number;
  /** 표시 포맷(기본 ko-KR 천단위 구분). */
  format?: (n: number) => string;
  durationMs?: number;
}

export function AnimatedCount({
  value,
  format = (n) => n.toLocaleString("ko-KR"),
  durationMs = 600,
  className,
  ...props
}: AnimatedCountProps) {
  const reduced = usePrefersReducedMotion();
  const [display, setDisplay] = React.useState(value);
  const fromRef = React.useRef(value);
  const rafRef = React.useRef<number | null>(null);

  React.useEffect(() => {
    const from = fromRef.current;
    if (from === value) return;

    // reduced-motion: 틱업 없이 즉시 갱신(카운트는 반드시 새 값으로 반영 — critic 지적 해소).
    if (reduced) {
      fromRef.current = value;
      setDisplay(value);
      return;
    }

    const start =
      typeof performance !== "undefined" && performance.now ? performance.now() : Date.now();
    const delta = value - from;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(from + delta * eased));
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = value;
        setDisplay(value);
      }
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [value, reduced, durationMs]);

  return (
    <span className={cn("tabular-nums", className)} {...props}>
      {format(display)}
    </span>
  );
}
