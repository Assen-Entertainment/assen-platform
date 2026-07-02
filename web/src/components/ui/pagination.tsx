import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronLeftIcon, ChevronRightIcon } from "@/lib/icons";

/** Pagination — 페이지 이동. total>7 시 현재 주변 + 양끝 + 생략(…). 제어형. */
export interface PaginationProps {
  page: number;
  total: number;
  onPage: (page: number) => void;
  className?: string;
}

function pageList(page: number, total: number): (number | "…")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const out: (number | "…")[] = [1];
  const lo = Math.max(2, page - 1);
  const hi = Math.min(total - 1, page + 1);
  if (lo > 2) out.push("…");
  for (let p = lo; p <= hi; p++) out.push(p);
  if (hi < total - 1) out.push("…");
  out.push(total);
  return out;
}

const btn = "flex size-9 items-center justify-center rounded-md text-label transition-colors";

export function Pagination({ page, total, onPage, className }: PaginationProps) {
  return (
    <nav aria-label="페이지" className={cn("flex items-center gap-1", className)}>
      <button type="button" aria-label="이전" disabled={page <= 1} onClick={() => onPage(page - 1)} className={cn(btn, "text-on-surface-variant hover:bg-surface-container-high disabled:pointer-events-none disabled:opacity-[0.38]")}>
        <ChevronLeftIcon className="size-5" />
      </button>
      {pageList(page, total).map((p, i) =>
        p === "…" ? (
          <span key={`e${i}`} className="flex size-9 items-center justify-center text-on-surface-variant">
            …
          </span>
        ) : (
          <button
            key={p}
            type="button"
            aria-current={p === page ? "page" : undefined}
            onClick={() => onPage(p)}
            className={cn(btn, p === page ? "bg-primary text-on-primary" : "text-on-surface hover:bg-surface-container-high")}
          >
            {p}
          </button>
        ),
      )}
      <button type="button" aria-label="다음" disabled={page >= total} onClick={() => onPage(page + 1)} className={cn(btn, "text-on-surface-variant hover:bg-surface-container-high disabled:pointer-events-none disabled:opacity-[0.38]")}>
        <ChevronRightIcon className="size-5" />
      </button>
    </nav>
  );
}
