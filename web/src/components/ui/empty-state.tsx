import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * EmptyState — Figma DS(39:9). [분류] 유틸/피드백형 → 루브릭 A·D·E 중심(B·C는 N/A; 크리에이터 시그니처 책임 없음).
 * [브랜드 루브릭] D warmth: 아이콘 서클 primary-container 틴트(중립 회색 탈피)·친근 카피·CTA.
 *  ※Figma 원본은 회색 서클·fs12 → warmth 상향(Figma 동기 권고).
 */
export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ icon, title, description, action, className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex flex-col items-center gap-2.5 px-6 py-8 text-center", className)}
      {...props}
    >
      <div className="mb-1 flex size-14 items-center justify-center rounded-full bg-primary-container text-on-primary-container">
        {icon}
      </div>
      <h3 className="text-title-m text-on-surface">{title}</h3>
      {description ? <p className="max-w-xs text-body-s text-on-surface-variant">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  ),
);
EmptyState.displayName = "EmptyState";
