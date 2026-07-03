import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * SuccessCheck — 성취 순간(결제완료·후원완료) 딜라이트(루브릭 #41).
 * gradient.brand 원 + stroke-dashoffset 드로우 애니메이션. 원은 success-pop 으로 등장.
 * 모션 축소는 globals.css 전역 가드(prefers-reduced-motion)가 처리 → 즉시 표시(#43).
 */
const SIZES = { md: "size-16", lg: "size-20" } as const;

export interface SuccessCheckProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: keyof typeof SIZES;
  label?: string;
}

export const SuccessCheck = React.forwardRef<HTMLDivElement, SuccessCheckProps>(
  ({ size = "lg", label = "완료", className, ...props }, ref) => (
    <div
      ref={ref}
      role="img"
      aria-label={label}
      className={cn(
        "flex items-center justify-center rounded-full text-white [animation:success-pop_320ms_ease-out]",
        SIZES[size],
        className,
      )}
      style={{ backgroundImage: "var(--gradient-brand)" }}
      {...props}
    >
      <svg viewBox="0 0 24 24" className="size-1/2" fill="none" stroke="currentColor" strokeWidth={3} aria-hidden>
        <path
          d="M5 13l4 4L19 7"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ strokeDasharray: 32, animation: "check-draw 420ms ease-out 120ms both" }}
        />
      </svg>
    </div>
  ),
);
SuccessCheck.displayName = "SuccessCheck";
