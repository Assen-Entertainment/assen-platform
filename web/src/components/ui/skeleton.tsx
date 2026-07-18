import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Skeleton — Figma DS Skeleton(52:8). 톤 베이스(surface-container-high) + 부드러운 샤인 스윕(P3).
 * 예전 flat animate-pulse → 미니멀 럭셔리 톤 샤인(커버 톤 언어와 일관). reduced-motion 시 정적 톤(모션 0).
 */
export const Skeleton = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      aria-hidden
      className={cn("skeleton-shimmer rounded-sm bg-surface-container-high motion-reduce:animate-none", className)}
      {...props}
    />
  ),
);
Skeleton.displayName = "Skeleton";
