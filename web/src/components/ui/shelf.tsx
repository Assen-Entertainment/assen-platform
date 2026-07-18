import * as React from "react";
import { cn } from "@/lib/utils";
import { SectionHeader } from "@/components/ui/section-header";

/**
 * Shelf — 큐레이션 선반 레일(루브릭 #10, Patreon shelves 참조).
 * SectionHeader + 가로 스크롤 트랙(scroll-snap + 스크롤바 숨김). 인기/신규/추천을 스캔.
 * children 은 고정폭 카드(예: w-40)를 넣어 가로로 스냅 스크롤한다.
 */
export interface ShelfProps extends React.HTMLAttributes<HTMLElement> {
  title: string;
  description?: string;
  action?: React.ReactNode;
  as?: "h2" | "h3";
}

export const Shelf = React.forwardRef<HTMLElement, ShelfProps>(
  ({ title, description, action, as = "h2", className, children, ...props }, ref) => (
    <section ref={ref} className={cn("flex flex-col gap-3", className)} {...props}>
      <SectionHeader as={as} title={title} description={description} action={action} />
      <div
        className="no-scrollbar -mx-1 flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-px-1 px-1 pb-1"
        role="list"
      >
        {React.Children.map(children, (child) =>
          child == null ? null : (
            <div role="listitem" className="shrink-0 snap-start">
              {child}
            </div>
          ),
        )}
      </div>
    </section>
  ),
);
Shelf.displayName = "Shelf";
