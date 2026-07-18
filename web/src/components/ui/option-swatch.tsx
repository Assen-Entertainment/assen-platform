import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * OptionSwatch — Figma DS(60:3). 상품 옵션 선택 스와치(색·타입).
 * selected=primary 틴트/보더, disabled=품절(취소선). aria-pressed 로 선택 상태 전달.
 */
export interface OptionSwatchProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  selected?: boolean;
}

export const OptionSwatch = React.forwardRef<HTMLButtonElement, OptionSwatchProps>(
  ({ selected, disabled, className, type = "button", children, ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      disabled={disabled}
      aria-pressed={selected}
      className={cn(
        "inline-flex h-9 items-center justify-center rounded-md border px-3 text-body-s transition-colors",
        "disabled:pointer-events-none disabled:text-on-surface-variant disabled:line-through disabled:opacity-60",
        selected
          ? "border-primary bg-primary-container text-on-primary-container"
          : "border-outline bg-surface text-on-surface hover:bg-surface-container-high",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  ),
);
OptionSwatch.displayName = "OptionSwatch";
