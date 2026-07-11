import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { gradientStyle } from "@/lib/placeholder";

/**
 * MonetizableItem — Figma DS MonetizableItem 세트(260:28) 매핑.
 * 유연 수익 아이템 공통 카드: 굿즈/디지털/체험/티켓/쿠폰/멤버십.
 * Figma 프로퍼티 ↔ props: type(변형)·title(Title)·price(Price)·meta(Meta).
 * 타입별 태그/CTA 라벨은 type 에서 파생(Figma 변형 규칙과 동일).
 */
export type MonetizableItemType =
  | "goods"
  | "digital"
  | "experience"
  | "ticket"
  | "coupon"
  | "membership";

const TYPE_META: Record<MonetizableItemType, { tag: string; cta: string }> = {
  goods: { tag: "굿즈", cta: "구매" },
  digital: { tag: "디지털", cta: "구매" },
  experience: { tag: "체험", cta: "예약" },
  ticket: { tag: "티켓", cta: "구매" },
  coupon: { tag: "쿠폰", cta: "받기" },
  membership: { tag: "멤버십", cta: "구독" },
};

export interface MonetizableItemProps extends React.HTMLAttributes<HTMLDivElement> {
  type: MonetizableItemType;
  title: string;
  price: string;
  meta?: string;
  /** 썸네일/이미지 노드. 없으면 surface-container-high placeholder. */
  media?: React.ReactNode;
  /** 크리에이터 표기 슬롯(이름/프로필 링크 등) — 있을 때만 제목 아래 노출. 전역 상품은 생략. */
  creator?: React.ReactNode;
  /** 기본 CTA 라벨은 type 파생; 필요 시 오버라이드. */
  ctaLabel?: string;
  /** CTA 비활성 — 상위 게이트(예: 배송 결제 준비 중)에서 액션을 막을 때. 라벨은 ctaLabel로 함께 조정. */
  actionDisabled?: boolean;
  onAction?: () => void;
}

export const MonetizableItem = React.forwardRef<HTMLDivElement, MonetizableItemProps>(
  ({ type, title, price, meta, media, creator, ctaLabel, actionDisabled, onAction, className, ...props }, ref) => {
    const t = TYPE_META[type];
    return (
      <div
        ref={ref}
        className={cn(
          "group flex w-full flex-col overflow-hidden rounded-lg border border-outline bg-surface transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-2 motion-reduce:transform-none motion-reduce:transition-none",
          className,
        )}
        {...props}
      >
        <div
          className="relative aspect-[5/3] w-full overflow-hidden bg-surface-container-high"
          style={media ? undefined : gradientStyle(title)}
        >
          {media}
          {/* 타입 태그 — 미디어 위 프로스티드 칩(임의 커버색 위에서도 가독). */}
          <span className="absolute left-2.5 top-2.5 rounded-full bg-surface/85 px-2.5 py-1 text-caption font-medium text-on-surface shadow-1 backdrop-blur-sm">
            {t.tag}
          </span>
        </div>
        <div className="flex flex-col gap-1.5 p-3.5">
          <h3 className="line-clamp-1 text-title-m text-on-surface">{title}</h3>
          {creator ? <div className="line-clamp-1 text-body-s text-on-surface-variant">{creator}</div> : null}
          {meta ? (
            <p className="line-clamp-1 text-body-s text-on-surface-variant">{meta}</p>
          ) : null}
          <div className="mt-1.5 flex items-center justify-between gap-2">
            <span className="text-title-l tabular-nums text-on-surface">{price}</span>
            <Button size="sm" onClick={onAction} disabled={actionDisabled}>
              {ctaLabel ?? t.cta}
            </Button>
          </div>
        </div>
      </div>
    );
  },
);
MonetizableItem.displayName = "MonetizableItem";
