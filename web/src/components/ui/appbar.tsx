import * as React from "react";
import { cn } from "@/lib/utils";

/** AppBar — Figma DS AppBar(17:19). 모바일 상단(56). leading(뒤로) + title + trailing(액션). */
export interface AppBarProps extends React.HTMLAttributes<HTMLElement> {
  title?: string;
  leading?: React.ReactNode;
  trailing?: React.ReactNode;
}

export function AppBar({ title, leading, trailing, className, ...props }: AppBarProps) {
  return (
    <header className={cn("flex h-14 items-center gap-2 border-b border-outline bg-surface px-2", className)} {...props}>
      <div className="flex w-10 shrink-0 items-center justify-center">{leading}</div>
      {title ? (
        <h1 className="flex-1 truncate text-center text-title-m text-on-surface">{title}</h1>
      ) : (
        <div className="flex-1" />
      )}
      <div className="flex min-w-10 shrink-0 items-center justify-end gap-1">{trailing}</div>
    </header>
  );
}
