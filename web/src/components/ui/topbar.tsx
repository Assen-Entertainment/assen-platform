import * as React from "react";
import { cn } from "@/lib/utils";

/** TopBar — 웹 셸. 좌(선택 로고) + 중앙 검색 + 우 액션(알림·프로필·CTA). 로고는 보통 Sidebar에. */
export interface TopBarProps extends React.HTMLAttributes<HTMLElement> {
  logo?: React.ReactNode;
  search?: React.ReactNode;
  actions?: React.ReactNode;
}

export function TopBar({ logo, search, actions, className, ...props }: TopBarProps) {
  return (
    <header className={cn("flex h-16 shrink-0 items-center gap-4 border-b border-outline bg-surface px-6", className)} {...props}>
      {logo ? <div className="shrink-0">{logo}</div> : null}
      {search ? <div className="flex flex-1 justify-center">{search}</div> : <div className="flex-1" />}
      {actions ? <div className="flex shrink-0 items-center gap-3">{actions}</div> : null}
    </header>
  );
}
