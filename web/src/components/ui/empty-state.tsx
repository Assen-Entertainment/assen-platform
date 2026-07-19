import * as React from "react";
import { cn } from "@/lib/utils";
import { InboxLineIcon } from "@/components/ui/empty-state-icons";

/**
 * EmptyState — Figma DS(39:9). [분류] 유틸/피드백형 → 루브릭 A·D·E 중심(B·C는 N/A).
 *
 * [한 규격(P·빈상태 크래프트)] "모든 픽셀이 의도됐는가"를 위해 원판·아이콘·타이포·CTA 리듬을 단일 스펙으로 고정한다.
 *  - 원판: size-14(56px) · surface-container-high 중립 톤 + ring-outline 헤어라인(과채도 브랜드 틴트 배제 = 미니멀 럭셔리).
 *  - 아이콘: 미전달 시 라인 아이콘 폴백(InboxLineIcon) → 민 원판("깨진 이미지") 제거. 크기는 [&>svg]:size-6(24px)로 통일.
 *  - 카피: 타이틀(title-m) + 설명(body-s, text-pretty) + 선택 CTA. 리듬은 명시 마진으로 의도적으로 배치.
 * 색은 기존 토큰만 사용(브랜드 신규색 0). 브랜드는 CTA(primary)에서만 발화한다.
 */
export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 컨텍스트 라인 아이콘(@/components/ui/empty-state-icons). 미전달 시 InboxLineIcon 폴백. */
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ icon, title, description, action, className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex flex-col items-center px-6 py-10 text-center", className)}
      {...props}
    >
      <div
        aria-hidden
        className="mb-4 flex size-14 items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant ring-1 ring-inset ring-outline [&>svg]:size-6"
      >
        {icon ?? <InboxLineIcon />}
      </div>
      <h3 className="text-title-m text-on-surface">{title}</h3>
      {description ? (
        <p className="mt-1.5 max-w-xs text-pretty text-body-s text-on-surface-variant">{description}</p>
      ) : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  ),
);
EmptyState.displayName = "EmptyState";
