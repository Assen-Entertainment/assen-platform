import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * StatusChip — Figma DS StatusChip(206:34). 상태 점 + 라벨(주문/정산/스튜디오 상태).
 * 4변형: neutral(대기·취소) · info(진행중) · success(완료) · danger(실패·거절).
 * 컨테이너 토큰 재사용(Badge와 동일 팔레트) + 상태 점으로 스캔성 강화.
 */
const statusChipVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-caption font-medium",
  {
    variants: {
      variant: {
        neutral: "bg-surface-container-high text-on-surface-variant",
        info: "bg-primary-container text-on-primary-container",
        success: "bg-success-container text-on-success-container",
        danger: "bg-error-container text-on-error-container",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

const DOT: Record<NonNullable<StatusChipProps["variant"]>, string> = {
  neutral: "bg-on-surface-variant",
  info: "bg-primary",
  success: "bg-success",
  danger: "bg-error",
};

export type StatusChipVariant = "neutral" | "info" | "success" | "danger";

export interface StatusChipProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof statusChipVariants> {
  /** 상태 점 표시(기본 true). */
  dot?: boolean;
}

export const StatusChip = React.forwardRef<HTMLSpanElement, StatusChipProps>(
  ({ className, variant, dot = true, children, ...props }, ref) => (
    <span ref={ref} className={cn(statusChipVariants({ variant }), className)} {...props}>
      {dot ? <span className={cn("size-1.5 rounded-full", DOT[variant ?? "neutral"])} aria-hidden /> : null}
      {children}
    </span>
  ),
);
StatusChip.displayName = "StatusChip";

export { statusChipVariants };
