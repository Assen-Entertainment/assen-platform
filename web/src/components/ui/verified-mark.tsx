import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * VerifiedMark — Figma DS VerifiedMark(51:11). 인증 크리에이터 체크 배지(단독형).
 * Avatar 내장 배지와 달리 이름 옆 인라인 표기에 사용. primary 원 + 흰 체크.
 */
const SIZES = { sm: "size-4", md: "size-5" } as const;

export interface VerifiedMarkProps extends React.HTMLAttributes<HTMLSpanElement> {
  size?: keyof typeof SIZES;
  label?: string;
}

export const VerifiedMark = React.forwardRef<HTMLSpanElement, VerifiedMarkProps>(
  ({ size = "sm", label = "인증됨", className, ...props }, ref) => (
    <span
      ref={ref}
      role="img"
      aria-label={label}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full bg-primary text-on-primary",
        SIZES[size],
        className,
      )}
      {...props}
    >
      <svg viewBox="0 0 24 24" className="size-[62%]" fill="none" stroke="currentColor" strokeWidth={3}>
        <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  ),
);
VerifiedMark.displayName = "VerifiedMark";
