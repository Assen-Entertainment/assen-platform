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
  /** perk 빌드업 시각화(루브릭 #15) — 예: "라이트 혜택 포함". 상위 티어가 하위 perk 누적임을 표기. */
  inheritNote?: string;
  ctaLabel?: string;
  onSubscribe?: () => void;
}

/** 가격 표기 포맷 — 숫자면 천 단위 구분, 문자열이면 그대로. (₩ 접두는 소비 측에서). */
function formatPrice(v: number | string): string {
  return typeof v === "number" ? v.toLocaleString("ko-KR") : v;
}

export const MembershipTierCard = React.forwardRef<HTMLDivElement, MembershipTierCardProps>(
  (
    { name, price, period = "월", benefits, badge, featured, accent, inheritNote, ctaLabel = "구독하기", onSubscribe, className, ...props },
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
          <span className={cn("text-display-m tabular-nums", accent ? "text-creator-accent" : "text-primary")}>₩{formatPrice(price)}</span>
          {period ? <span className="text-body-m text-on-surface-variant">/{period}</span> : null}
        </div>
        <div className="h-px w-full bg-outline" />
        {inheritNote ? (
          <p
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-body-s",
              accent ? "bg-creator-accent-container text-on-creator-accent-container" : "bg-primary-container text-on-primary-container",
            )}
          >
            <svg viewBox="0 0 24 24" className="size-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} aria-hidden>
              <path d="M12 5v14M5 12h14" strokeLinecap="round" />
            </svg>
            {inheritNote}
          </p>
        ) : null}
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
