import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "./button";
import { ErrorIcon } from "@/lib/icons";

/**
 * ErrorState — Figma DS(116:13). 인라인 에러 피드백(아이콘+메시지+재시도).
 * EmptyState 스타일 준용하되 아이콘 서클은 error-container 틴트로 상태를 전달.
 * 데이터 로드 실패 시 뷰 내부에서 사용(재시도=RQ refetch 배선).
 */
export interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title?: string;
  description?: string;
  /** 재시도 핸들러 — 지정 시 재시도 버튼 노출. */
  onRetry?: () => void;
  retryLabel?: string;
}

export const ErrorState = React.forwardRef<HTMLDivElement, ErrorStateProps>(
  (
    {
      icon,
      title = "불러오지 못했어요",
      description = "잠시 후 다시 시도해 주세요.",
      onRetry,
      retryLabel = "다시 시도",
      className,
      ...props
    },
    ref,
  ) => (
    <div
      ref={ref}
      role="alert"
      className={cn("flex flex-col items-center gap-2.5 px-6 py-8 text-center", className)}
      {...props}
    >
      <div className="mb-1 flex size-14 items-center justify-center rounded-full bg-error-container text-on-error-container">
        {icon ?? <ErrorIcon className="size-7" />}
      </div>
      <h3 className="text-title-m text-on-surface">{title}</h3>
      {description ? <p className="max-w-xs text-body-s text-on-surface-variant">{description}</p> : null}
      {onRetry ? (
        <Button variant="outline" className="mt-2" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
    </div>
  ),
);
ErrorState.displayName = "ErrorState";
