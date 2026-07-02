import * as React from "react";
import { cn } from "@/lib/utils";

/** BottomNav — Figma DS BottomNavBar(17:3). 모바일 하단 5탭, 활성=primary. 제어형(activeHref). */
export interface BottomNavItem {
  icon: React.ReactNode;
  label: string;
  href: string;
}
export interface BottomNavProps extends React.HTMLAttributes<HTMLElement> {
  items: BottomNavItem[];
  activeHref?: string;
}

export function BottomNav({ items, activeHref, className, ...props }: BottomNavProps) {
  return (
    <nav aria-label="하단 탐색" className={cn("flex h-16 items-stretch border-t border-outline bg-surface", className)} {...props}>
      {items.map((it) => {
        const active = it.href === activeHref;
        return (
          <a
            key={it.href}
            href={it.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex flex-1 flex-col items-center justify-center gap-1 text-caption transition-colors [&>span>svg]:size-6",
              active ? "text-primary" : "text-on-surface-variant",
            )}
          >
            <span>{it.icon}</span>
            {it.label}
          </a>
        );
      })}
    </nav>
  );
}
