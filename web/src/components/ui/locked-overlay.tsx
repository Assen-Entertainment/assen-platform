import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * LockedOverlay — Figma DS(53:8). 잠긴 콘텐츠 위 오버레이(블러 + 락 + 해제 CTA).
 * 부모 요소에 `relative` 필요. 잠금 상품/멤버십 전용 콘텐츠(루브릭 #16)에 사용.
 */
export interface LockedOverlayProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  description?: string;
  /** 해제 CTA(예: 멤버십 구독 버튼). */
  cta?: React.ReactNode;
}

export const LockedOverlay = React.forwardRef<HTMLDivElement, LockedOverlayProps>(
  ({ title = "멤버십 전용 콘텐츠", description, cta, className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 rounded-[inherit] bg-surface/70 p-6 text-center backdrop-blur-md",
        className,
      )}
      {...props}
    >
      <span className="flex size-11 items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant">
        <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
          <rect x="5" y="11" width="14" height="9" rx="2" />
          <path d="M8 11V8a4 4 0 0 1 8 0v3" strokeLinecap="round" />
        </svg>
      </span>
      <p className="text-title-m text-on-surface">{title}</p>
      {description ? <p className="max-w-xs text-body-s text-on-surface-variant">{description}</p> : null}
      {cta ? <div className="mt-1">{cta}</div> : null}
    </div>
  ),
);
LockedOverlay.displayName = "LockedOverlay";
