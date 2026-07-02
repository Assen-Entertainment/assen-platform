import * as React from "react";
import { cn } from "@/lib/utils";

/** Spinner — Figma DS Spinner(50:7). primary 회전 arc. reduced-motion 시 정지. */
export function Spinner({ className, ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      role="status"
      aria-label="로딩 중"
      className={cn("size-6 animate-spin text-primary motion-reduce:animate-none", className)}
      {...props}
    >
      <circle cx="12" cy="12" r="9" className="opacity-20" stroke="currentColor" strokeWidth="3" fill="none" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" fill="none" />
    </svg>
  );
}
