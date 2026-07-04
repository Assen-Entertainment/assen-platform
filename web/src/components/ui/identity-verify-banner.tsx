import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * IdentityVerifyBanner — Figma DS(41:15). 본인인증 상태 안내 배너.
 * 성인 콘텐츠·고액 결제 등에서 노출. `verified`에 따라 문구/톤을 분기(미인증=경고 + action, 완료=성공).
 * ※실 provider(PASS/NICE/KCB) 연동은 명시적 게이트 — mock 인증만 배선됨.
 */
export interface IdentityVerifyBannerProps extends React.HTMLAttributes<HTMLDivElement> {
  action?: React.ReactNode;
  /** 본인인증 완료 여부 — 문구/톤 분기(기본 미인증). */
  verified?: boolean;
}

export const IdentityVerifyBanner = React.forwardRef<HTMLDivElement, IdentityVerifyBannerProps>(
  ({ action, verified = false, className, ...props }, ref) => (
    <div
      ref={ref}
      role="note"
      className={cn(
        "flex items-center gap-3 rounded-lg border p-3",
        verified
          ? "border-success bg-success-container text-on-success-container"
          : "border-warning bg-warning-container text-on-warning-container",
        className,
      )}
      {...props}
    >
      <svg viewBox="0 0 24 24" className="size-5 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
        <path d="M12 3l8 4v5c0 4.5-3 7.5-8 9-5-1.5-8-4.5-8-9V7z" strokeLinejoin="round" />
        <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="flex-1 text-body-s">
        {verified ? (
          <>
            <p className="font-medium">본인인증이 완료되었어요</p>
            <p className="text-caption opacity-90">성인(19+) 콘텐츠와 인증이 필요한 결제를 이용할 수 있어요.</p>
          </>
        ) : (
          <>
            <p className="font-medium">본인인증이 필요해요</p>
            <p className="text-caption opacity-90">일부 상품·결제와 성인(19+) 콘텐츠는 본인인증 후 이용할 수 있어요.</p>
          </>
        )}
      </div>
      {verified ? null : action}
    </div>
  ),
);
IdentityVerifyBanner.displayName = "IdentityVerifyBanner";
