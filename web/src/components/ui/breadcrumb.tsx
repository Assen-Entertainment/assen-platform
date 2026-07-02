import * as React from "react";
import { cn } from "@/lib/utils";

/** Breadcrumb — 웹 경로 탐색. 마지막=현재(aria-current). */
export interface Crumb {
  label: string;
  href?: string;
}

export function Breadcrumb({ items, className }: { items: Crumb[]; className?: string }) {
  return (
    <nav aria-label="브레드크럼" className={cn("flex flex-wrap items-center gap-1.5 text-body-s text-on-surface-variant", className)}>
      {items.map((c, i) => {
        const last = i === items.length - 1;
        return (
          <span key={i} className="flex items-center gap-1.5">
            {c.href && !last ? (
              <a href={c.href} className="transition-colors hover:text-on-surface">
                {c.label}
              </a>
            ) : (
              <span className={last ? "text-on-surface" : undefined} aria-current={last ? "page" : undefined}>
                {c.label}
              </span>
            )}
            {!last ? <span aria-hidden>/</span> : null}
          </span>
        );
      })}
    </nav>
  );
}
