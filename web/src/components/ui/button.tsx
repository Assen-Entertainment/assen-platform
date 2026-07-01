import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Button — Figma DS Button(9:8) 매핑. 토큰 바인딩(primary/surface/outline), pill/md/lg.
 * asChild 로 링크 등에 합성(Radix Slot). disabled = state.disabledOpacity 0.38.
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-[background-color,opacity] disabled:pointer-events-none disabled:opacity-[0.38]",
  {
    variants: {
      variant: {
        primary: "bg-primary text-on-primary hover:opacity-90",
        secondary: "bg-surface-container-high text-on-surface hover:bg-outline",
        outline: "border border-outline bg-surface text-on-surface hover:bg-surface-container-high",
        ghost: "text-on-surface hover:bg-surface-container-high",
        accent: "bg-creator-accent text-on-creator-accent hover:opacity-90",
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
