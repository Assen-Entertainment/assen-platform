import * as React from "react";
import { cn } from "@/lib/utils";
import { WarningIcon } from "@/lib/icons";

/**
 * DisclaimerNotice — Figma DS DisclaimerNotice(41:10). 게이트/placeholder 고지 박스.
 * 수수료·약관·가격 등 "단독 확정 금지" 항목이나 데모 한계를 알리는 중립 경고 톤.
 * ※문구는 법무·대표 검토 전 placeholder 임을 표기하는 용도.
 */
export interface DisclaimerNoticeProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title?: string;
  children: React.ReactNode;
}

export const DisclaimerNotice = React.forwardRef<HTMLDivElement, DisclaimerNoticeProps>(
  ({ icon, title, children, className, ...props }, ref) => (
    <div
      ref={ref}
      role="note"
      className={cn(
        "flex items-start gap-2.5 rounded-md border border-warning-container bg-warning-container/40 px-3.5 py-3 text-on-surface",
        className,
      )}
      {...props}
    >
      <span className="mt-0.5 shrink-0 text-warning [&>svg]:size-5">{icon ?? <WarningIcon />}</span>
      <div className="flex min-w-0 flex-col gap-0.5">
        {title ? <span className="text-label text-on-surface">{title}</span> : null}
        <p className="text-body-s text-on-surface-variant">{children}</p>
      </div>
    </div>
  ),
);
DisclaimerNotice.displayName = "DisclaimerNotice";
