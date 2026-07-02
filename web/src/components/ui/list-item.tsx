import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronRightIcon } from "@/lib/icons";

/** ListItem — Figma DS(15:4). leading + (title/subtitle) + trailing/chevron. 마이/설정 등. */
export interface ListItemProps extends React.HTMLAttributes<HTMLDivElement> {
  leading?: React.ReactNode;
  title: string;
  subtitle?: string;
  trailing?: React.ReactNode;
  showChevron?: boolean;
}

export const ListItem = React.forwardRef<HTMLDivElement, ListItemProps>(
  ({ leading, title, subtitle, trailing, showChevron, className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center gap-3 px-4 py-3", className)} {...props}>
      {leading ? <div className="shrink-0">{leading}</div> : null}
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="line-clamp-1 text-body-l text-on-surface">{title}</span>
        {subtitle ? <span className="line-clamp-1 text-caption text-on-surface-variant">{subtitle}</span> : null}
      </div>
      {trailing ? <div className="shrink-0 text-on-surface-variant">{trailing}</div> : null}
      {showChevron ? <ChevronRightIcon className="size-5 shrink-0 text-on-surface-variant" /> : null}
    </div>
  ),
);
ListItem.displayName = "ListItem";
