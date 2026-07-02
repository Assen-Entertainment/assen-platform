import * as React from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

/**
 * MembershipTierCard — Figma DS(19:3). surfaceContainer·radius lg·outline, 가격 Display/M.
 * [브랜드 루브릭] B 시그니처: featured 티어 강조 바/보더. C 크리에이터: accent=true → 크리에이터 액센트로 강조
 *  (creatorAccentVars 스코프 내에서 의미). 기본 false=primary/gradient.brand(전역 chrome). A: 가격 tabular. D: 혜택 체크.
 */
export interface MembershipTierCardProps extends React.HTMLAttributes<HTMLDivElement> {
  name: string;
  price: number | string;
  period?: string;
  benefits: string[];
  badge?: string;
  featured?: boolean;
  /** featured 강조를 크리에이터 액센트로(상위 creatorAccentVars 스코프 필요). 미지정 시 primary/gradient.brand. */
  accent?: boolean;
  ctaLabel?: string;
  onSubscribe?: () => void;
}

function won(v: number | string): string {
  return typeof v === "number" ? v.toLocaleString("ko-KR") : v;
}

export const MembershipTierCard = React.forwardRef<HTMLDivElement, MembershipTierCardProps>(
  (
    { name, price, period = "월", benefits, badge, featured, accent, ctaLabel = "구독하기", onSubscribe, className, ...props },
    ref,
  ) => (
    <div
      ref={ref}
      className={cn(
        "flex w-full flex-col overflow-hidden rounded-lg border bg-surface-container",
        featured ? (accent ? "border-creator-accent shadow-2" : "border-primary shadow-2") : "border-outline",
        className,
      )}
      {...props}
    >
      {featured ? (
        <div
          className="h-1.5 w-full"
          style={accent ? { backgroundColor: "var(--creator-accent)" } : { backgroundImage: "var(--gradient-brand)" }}
        />
      ) : null}
      <div className="flex flex-col gap-4 p-5">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-title-l text-on-surface">{name}</h3>
          {badge ? <Badge variant="primary">{badge}</Badge> : null}
        </div>
        <div className="flex items-baseline gap-1">
          <span className={cn("text-display-m tabular-nums", accent ? "text-creator-accent" : "text-primary")}>₩{won(price)}</span>
          {period ? <span className="text-body-m text-on-surface-variant">/{period}</span> : null}
        </div>
        <div className="h-px w-full bg-outline" />
        <ul className="flex flex-col gap-2">
          {benefits.map((b, i) => (
            <li key={`${b}-${i}`} className="flex items-center gap-2 text-body-m text-on-surface">
              <svg
                viewBox="0 0 24 24"
                className={cn("size-4 shrink-0", accent ? "text-creator-accent" : "text-primary")}
                fill="none"
                stroke="currentColor"
                strokeWidth={3}
              >
                <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              {b}
            </li>
          ))}
        </ul>
        <Button variant={featured ? (accent ? "accent" : "primary") : "secondary"} size="lg" className="w-full" onClick={onSubscribe}>
          {ctaLabel}
        </Button>
      </div>
    </div>
  ),
);
MembershipTierCard.displayName = "MembershipTierCard";
