import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * SectionHeader — Figma DS SectionHeader(86:15). 섹션 제목(+설명) + 우측 액션(더보기 링크/버튼) 슬롯.
 * 선반 레일·스튜디오 서브섹션 헤더 등에 사용.
 */
export interface SectionHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  action?: React.ReactNode;
  /** 제목 태그 — 페이지 heading 구조에 맞춰 조정(기본 h2). */
  as?: "h2" | "h3";
}

export const SectionHeader = React.forwardRef<HTMLDivElement, SectionHeaderProps>(
  ({ title, description, action, as: Tag = "h2", className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-end justify-between gap-3", className)} {...props}>
      <div className="flex min-w-0 flex-col gap-0.5">
        <Tag className="text-balance text-title-l text-on-surface">{title}</Tag>
        {description ? <p className="line-clamp-1 text-body-s text-on-surface-variant">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  ),
);
SectionHeader.displayName = "SectionHeader";
