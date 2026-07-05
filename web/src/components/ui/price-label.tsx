import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * PriceLabel — Figma DS PriceLabel(51:10). 가격(onSurface) + 선택: 할인%(error)·원가(취소선,onSurfaceVariant)·접미(/월).
 * tabular-nums 로 자릿수 정렬.
 */
export interface PriceLabelProps extends React.HTMLAttributes<HTMLSpanElement> {
  amount: number | string;
  currency?: string;
  suffix?: string;
  originalAmount?: number | string;
  discountPercent?: number;
}

function fmt(a: number | string): string {
  return typeof a === "number" ? a.toLocaleString("ko-KR") : a;
}

export const PriceLabel = React.forwardRef<HTMLSpanElement, PriceLabelProps>(
  ({ amount, currency = "₩", suffix, originalAmount, discountPercent, className, ...props }, ref) => (
    <span ref={ref} className={cn("inline-flex items-baseline gap-1 tabular-nums", className)} {...props}>
      {discountPercent ? (
        <span className="text-title-m font-bold text-error">{discountPercent}%</span>
      ) : null}
      <span className="text-title-m text-on-surface">
        {currency}
        {fmt(amount)}
      </span>
      {suffix ? <span className="text-body-s text-on-surface-variant">{suffix}</span> : null}
      {originalAmount != null ? (
        <span className="text-body-s text-on-surface-variant line-through">
          {currency}
          {fmt(originalAmount)}
        </span>
      ) : null}
    </span>
  ),
);
PriceLabel.displayName = "PriceLabel";
