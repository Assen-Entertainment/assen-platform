import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Button — Figma DS Button(9:8) 매핑. 토큰 바인딩(primary/surface/outline), pill/md/lg.
 * asChild 로 링크 등에 합성(Radix Slot).
 * [P2b 인터랙션] hover=색조 시프트, press=미세 스케일(active:scale, reduced-motion 가드),
 * focus-visible=전역 브랜드 아웃라인(globals). disabled=희미한 0.38 페이드 대신 solid 뮤트 표면
 *   (surface-container-high + on-surface-variant 라벨) → 라벨이 표면 대비 ≥3:1(라이트 3.9·다크 5.9)로
 *   또렷이 "비활성"으로 읽힌다(로그인 submit 저대비 개선).
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-[background-color,border-color,box-shadow,transform] active:scale-[0.98] motion-reduce:active:scale-100 disabled:pointer-events-none disabled:border-transparent disabled:bg-surface-container-high disabled:text-on-surface-variant disabled:shadow-none",
  {
    variants: {
      variant: {
        // filled hover = Stripe식 색조 시프트(명도 ~8% darken 토큰). opacity 페이드 대신 tone shift.
        primary: "bg-primary text-on-primary hover:bg-primary-hover",
        secondary: "bg-surface-container-high text-on-surface hover:bg-outline",
        outline: "border border-outline bg-surface text-on-surface hover:bg-surface-container-high",
        ghost: "text-on-surface hover:bg-surface-container-high",
        accent: "bg-creator-accent text-on-creator-accent hover:bg-creator-accent-hover",
      },
      size: {
        sm: "h-8 rounded-full px-3.5 text-label", // pill (카드 CTA)
        md: "h-10 rounded-md px-4 text-label",
        lg: "h-12 rounded-md px-5 text-title-m",
        icon: "h-10 w-10 rounded-md",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
    );
  },
);
Button.displayName = "Button";

export { buttonVariants };
