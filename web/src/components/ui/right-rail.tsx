import * as React from "react";
import { cn } from "@/lib/utils";

/** RightRail — 웹 보조 셸(추천·퀘스트·광고 슬롯). lg+ 에서만 표시. */
export function RightRail({ className, children, ...props }: React.HTMLAttributes<HTMLElement>) {
  return (
    <aside
      className={cn("hidden w-72 shrink-0 flex-col gap-4 border-l border-outline p-4 lg:flex", className)}
      {...props}
    >
      {children}
    </aside>
  );
}
