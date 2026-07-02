import * as React from "react";
import { cn } from "@/lib/utils";

/** Sidebar — 웹 셸(웹UI_기획). 240px 네비, 활성=surfaceContainerHigh+primary. 제어형(activeHref). */
export interface SidebarNavItem {
  icon: React.ReactNode;
  label: string;
  href: string;
}
export interface SidebarProps extends React.HTMLAttributes<HTMLElement> {
  brand?: React.ReactNode;
  items: SidebarNavItem[];
  activeHref?: string;
  footer?: React.ReactNode;
}

export function Sidebar({ brand, items, activeHref, footer, className, ...props }: SidebarProps) {
  return (
    <nav aria-label="주요 탐색" className={cn("flex h-full w-60 shrink-0 flex-col gap-1 border-r border-outline bg-surface p-3", className)} {...props}>
      {brand ? <div className="px-2 py-3">{brand}</div> : null}
      {items.map((it) => {
        const active = it.href === activeHref;
        return (
          <a
            key={it.href}
            href={it.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2.5 text-label transition-colors [&>span>svg]:size-5",
              active ? "bg-surface-container-high text-primary" : "text-on-surface hover:bg-surface-container-high",
            )}
          >
            <span className="shrink-0">{it.icon}</span>
            {it.label}
          </a>
        );
      })}
      {footer ? <div className="mt-auto pt-2">{footer}</div> : null}
    </nav>
  );
}
