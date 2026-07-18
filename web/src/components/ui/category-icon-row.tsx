import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * CategoryIconRow — Figma DS(217:77). 디스커버리 상단 카테고리 아이콘 행(루브릭 #7).
 * 콜드스타트(비로그인) 사용자도 즉시 둘러볼 수 있는 탐색 진입점. 가로 스크롤(모바일)·클릭 → 탐색/필터.
 */
export interface CategoryItem {
  label: string;
  value: string;
  icon: React.ReactNode;
}

export interface CategoryIconRowProps extends Omit<React.HTMLAttributes<HTMLElement>, "onSelect"> {
  items: CategoryItem[];
  onSelect: (value: string) => void;
  /** a11y 그룹 라벨. */
  ariaLabel?: string;
}

export const CategoryIconRow = React.forwardRef<HTMLElement, CategoryIconRowProps>(
  ({ items, onSelect, ariaLabel = "카테고리", className, ...props }, ref) => (
    <nav ref={ref} aria-label={ariaLabel} className={cn("no-scrollbar -mx-1 overflow-x-auto px-1", className)} {...props}>
      <ul className="flex min-w-max gap-2 sm:gap-3">
        {items.map((it) => (
          <li key={it.value}>
            <button
              type="button"
              onClick={() => onSelect(it.value)}
              className="flex w-16 flex-col items-center gap-1.5 rounded-md p-1 text-on-surface-variant transition-colors hover:text-on-surface focus-visible:text-on-surface"
            >
              <span className="flex size-12 items-center justify-center rounded-full bg-surface-container-high text-on-surface transition-colors hover:bg-primary-container [&>svg]:size-6">
                {it.icon}
              </span>
              <span className="line-clamp-1 text-caption">{it.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  ),
);
CategoryIconRow.displayName = "CategoryIconRow";
