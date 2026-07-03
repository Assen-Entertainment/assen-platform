import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * PaymentIcon — Figma DS(64:15). 결제수단 표기.
 * 브랜드 로고 미보유 → 토큰 배지(약어)로 표기(placeholder). showLabel 로 라벨 병기.
 */
export type PaymentMethod = "card" | "bank" | "pay" | "point";

const METHOD_META: Record<PaymentMethod, { label: string; abbr: string }> = {
  card: { label: "신용/체크카드", abbr: "CARD" },
  bank: { label: "계좌이체", abbr: "BANK" },
  pay: { label: "간편결제", abbr: "PAY" },
  point: { label: "포인트", abbr: "P" },
};

export interface PaymentIconProps extends React.HTMLAttributes<HTMLSpanElement> {
  method: PaymentMethod;
  /** 라벨 텍스트 병기(기본 false=배지만). */
  showLabel?: boolean;
}

export function PaymentIcon({ method, showLabel, className, ...props }: PaymentIconProps) {
  const m = METHOD_META[method];
  return (
    <span className={cn("inline-flex items-center gap-2", className)} {...props}>
      <span
        aria-hidden
        className="inline-flex h-6 min-w-10 items-center justify-center rounded border border-outline bg-surface-container px-1.5 text-caption font-bold tracking-wide text-on-surface-variant"
      >
        {m.abbr}
      </span>
      {showLabel ? <span className="text-body-m text-on-surface">{m.label}</span> : <span className="sr-only">{m.label}</span>}
    </span>
  );
}
