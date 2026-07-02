import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/** Badge — Figma DS Badge(11:15). 상태/카운트 라벨. 필 배경 + on-container 잉크(전 variant AA). */
const badgeVariants = cva(
  "inline-flex items-center justify-center rounded-full px-2 py-0.5 text-caption font-medium",
  {
    variants: {
      variant: {
        neutral: "bg-surface-container-high text-on-surface-variant",
        primary: "bg-primary-container text-on-primary-container",
        success: "bg-success-container text-on-success-container",
        warning: "bg-warning-container text-on-warning-container",
        error: "bg-error-container text-on-error-container",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => (
    <span ref={ref} className={cn(badgeVariants({ variant }), className)} {...props} />
  ),
);
Badge.displayName = "Badge";

export { badgeVariants };
