import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * IdentityVerifyBanner — Figma DS(41:15). 본인인증 필요 안내 배너.
 * 성인 콘텐츠·고액 결제 등에서 노출. ※ 실제 인증(KYC) 연동은 게이트 — placeholder.
 */
export interface IdentityVerifyBannerProps extends React.HTMLAttributes<HTMLDivElement> {
  action?: React.ReactNode;
}

export const IdentityVerifyBanner = React.forwardRef<HTMLDivElement, IdentityVerifyBannerProps>(
  ({ action, className, ...props }, ref) => (
    <div
      ref={ref}
      role="note"
      className={cn(
        "flex items-center gap-3 rounded-lg border border-warning bg-warning-container p-3 text-on-warning-container",
        className,
      )}
      {...props}
    >
      <svg viewBox="0 0 24 24" className="size-5 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
        <path d="M12 3l8 4v5c0 4.5-3 7.5-8 9-5-1.5-8-4.5-8-9V7z" strokeLinejoin="round" />
        <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="flex-1 text-body-s">
        <p className="font-medium">본인인증이 필요할 수 있어요</p>
        <p className="text-caption opacity-90">일부 상품·결제는 본인인증 후 진행됩니다. (인증 연동 예정 — placeholder)</p>
      </div>
      {action}
    </div>
  ),
);
IdentityVerifyBanner.displayName = "IdentityVerifyBanner";
