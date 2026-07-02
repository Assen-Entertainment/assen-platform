import * as React from "react";
import { cn } from "@/lib/utils";

/** Skeleton — Figma DS Skeleton(52:8). surface-container-high pulse. reduced-motion 시 정적. */
export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden
      className={cn("animate-pulse rounded-sm bg-surface-container-high motion-reduce:animate-none", className)}
      {...props}
    />
  );
}
