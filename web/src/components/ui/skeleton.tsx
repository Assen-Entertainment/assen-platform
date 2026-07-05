import * as React from "react";
import { cn } from "@/lib/utils";

/** Skeleton — Figma DS Skeleton(52:8). surface-container-high pulse. reduced-motion 시 정적. */
export const Skeleton = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      aria-hidden
      className={cn("animate-pulse rounded-sm bg-surface-container-high motion-reduce:animate-none", className)}
      {...props}
    />
  ),
);
Skeleton.displayName = "Skeleton";
