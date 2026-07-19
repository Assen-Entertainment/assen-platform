import * as React from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

/**
 * MembershipTierCard — Figma DS(19:3). surfaceContainer·radius lg·outline, 가격 Display/M.
 * [브랜드 루브릭] B 시그니처: featured 티어 강조 바/보더. C 크리에이터: accent=true → 크리에이터 액센트로 강조
 *  (creatorAccentVars 스코프 내에서 의미). 기본 false=primary/gradient.brand(전역 chrome). A: 가격 tabular. D: 혜택 체크.
 * [CTA 위계] 구독은 크리에이터 플랫폼에서 LTV가 가장 큰 액션 → 회색 secondary(비활성과 혼동) 금지.
 *  featured=solid(primary/creator-accent, 최고 강조 앵커), 비featured=브랜드 아웃라인(border-primary·text-primary,
 *  다크에서 라벨 자동 리프트로 WCAG AA 유지). 일회성 "구매하기" primary와 최소 동급 이상으로 읽힌다.
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
  /** 현재 구독 중인 티어 — "구독 중" 배지 + CTA 비활성(중복 구독 방지). */
  currentPlan?: boolean;
  onSubscribe?: () => void;
}

/** 가격 표기 포맷 — 숫자면 천 단위 구분, 문자열이면 그대로. (₩ 접두는 소비 측에서). */
function formatPrice(v: number | string): string {
  return typeof v === "number" ? v.toLocaleString("ko-KR") : v;
}

export const MembershipTierCard = React.forwardRef<HTMLDivElement, MembershipTierCardProps>(
  (
    { name, price, period = "월", benefits, badge, featured, accent, inheritNote, ctaLabel = "구독하기", currentPlan, onSubscribe, className, ...props },
    ref,
  ) => (
    <div
      ref={ref}
      className={cn(
        // 카드 표면 규율(P2b) — 헤어라인 + hover 소프트 그림자 + 1px 리프트(MonetizableItem 과 동일 시스템).
        // h-full: 그리드 셀(StaggerItem)을 꽉 채워 3장 등높이 정렬(짧은 카드도 행 높이만큼 늘어남).
        "flex h-full w-full flex-col overflow-hidden rounded-lg border bg-surface-container transition-[transform,box-shadow,border-color] duration-200 hover:-translate-y-0.5 hover:shadow-2 motion-reduce:transform-none motion-reduce:transition-none",
        featured ? (accent ? "border-creator-accent shadow-2" : "border-primary shadow-2") : "border-outline-variant hover:border-outline",
        className,
      )}
      {...props}
    >
      {/* 상단 액센트 바 — featured=크리에이터 액센트/브랜드 그라디언트로 앵커를 강조.
          비featured도 동일 h-1.5를 투명(배경 없음)으로 렌더해 3장의 상단 baseline을 맞춘다
          (등높이 정렬: 강조를 높이 차이 없이 색으로만 표현). shrink-0로 flex 축소 방지. */}
      <div
        aria-hidden
        className="h-1.5 w-full shrink-0"
        style={
          featured
            ? accent
              ? { backgroundColor: "var(--creator-accent)" }
              : { backgroundImage: "var(--gradient-brand)" }
            : undefined
        }
      />
      <div className="flex flex-1 flex-col gap-4 p-5">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-title-l text-on-surface">{name}</h3>
          <div className="flex shrink-0 items-center gap-1.5">
            {currentPlan ? <Badge variant="success">구독 중</Badge> : null}
            {badge ? <Badge variant="primary">{badge}</Badge> : null}
          </div>
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
        <Button
          variant={featured ? (accent ? "accent" : "primary") : "outline"}
          size="lg"
          className={cn(
            // mt-auto: 콘텐츠(칩 유/무·혜택 개수)와 무관하게 CTA를 카드 하단에 고정 → 3장의 버튼이 한 y선 정렬.
            "mt-auto w-full",
            // 비featured 구독 CTA — 회색 secondary(비활성과 혼동) 대신 브랜드 아웃라인.
            // 라벨 text-primary 는 다크에서 globals(.dark .text-primary=primary-bright)가 자동 리프트 →
            // 라이트/다크 모두 WCAG AA. currentPlan(disabled)일 땐 muted 표면으로 남겨 "구독 중"을 또렷이.
            !featured && !currentPlan && "border-primary text-primary hover:border-primary hover:bg-primary-container",
          )}
          disabled={currentPlan}
          onClick={currentPlan ? undefined : onSubscribe}
        >
          {currentPlan ? "구독 중" : ctaLabel}
        </Button>
      </div>
    </div>
  ),
);
MembershipTierCard.displayName = "MembershipTierCard";
