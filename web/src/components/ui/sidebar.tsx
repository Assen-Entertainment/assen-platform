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
  /** 네비 링크 렌더러 주입 슬롯 — 기본 "a"(DS 이식성 보존). 앱에선 next/link를 주입해 클라 라우팅(풀 리로드 방지). */
  linkComponent?: React.ElementType;
}

export function Sidebar({ brand, items, activeHref, footer, className, linkComponent: LinkComponent = "a", ...props }: SidebarProps) {
  return (
    <nav aria-label="주요 탐색" className={cn("flex h-full w-60 shrink-0 flex-col gap-1 border-r border-outline bg-surface p-3", className)} {...props}>
      {brand ? <div className="px-2 py-3">{brand}</div> : null}
      {items.map((it) => {
        const active = it.href === activeHref;
        return (
          <LinkComponent
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
          </LinkComponent>
        );
      })}
      {footer ? <div className="mt-auto pt-2">{footer}</div> : null}
    </nav>
  );
}
