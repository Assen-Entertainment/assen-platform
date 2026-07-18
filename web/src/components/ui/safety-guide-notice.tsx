import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * SafetyGuideNotice — Figma DS SafetyGuideNotice(45:20). 안전/신뢰 안내 박스.
 * 신고·정산 투명성·안전결제 등 이용자 보호 안내를 primary 틴트로 차분히 전달(경고와 구분).
 */
export interface SafetyGuideNoticeProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title?: string;
  children: React.ReactNode;
}

/** 방패형 안전 아이콘(무의존 인라인 SVG). */
function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2}>
      <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z" strokeLinejoin="round" />
      <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export const SafetyGuideNotice = React.forwardRef<HTMLDivElement, SafetyGuideNoticeProps>(
  ({ icon, title, children, className, ...props }, ref) => (
    <div
      ref={ref}
      role="note"
      className={cn(
        "flex items-start gap-2.5 rounded-md border border-primary-container bg-primary-container/40 px-3.5 py-3",
        className,
      )}
      {...props}
    >
      <span className="mt-0.5 shrink-0 text-primary [&>svg]:size-5">{icon ?? <ShieldIcon className="size-5" />}</span>
      <div className="flex min-w-0 flex-col gap-0.5">
        {title ? <span className="text-label text-on-surface">{title}</span> : null}
        <p className="text-body-s text-on-surface-variant">{children}</p>
      </div>
    </div>
  ),
);
SafetyGuideNotice.displayName = "SafetyGuideNotice";
