import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

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
  /** 기본 CTA 라벨은 type 파생; 필요 시 오버라이드. */
  ctaLabel?: string;
  onAction?: () => void;
}

export const MonetizableItem = React.forwardRef<HTMLDivElement, MonetizableItemProps>(
  ({ type, title, price, meta, media, ctaLabel, onAction, className, ...props }, ref) => {
    const t = TYPE_META[type];
    return (
      <div
        ref={ref}
        className={cn(
          "flex w-full flex-col overflow-hidden rounded-lg border border-outline bg-surface",
          className,
        )}
        {...props}
      >
        <div className="aspect-[5/3] w-full bg-surface-container-high">{media}</div>
        <div className="flex flex-col gap-2 p-3">
          <Badge variant="primary" className="self-start">
            {t.tag}
          </Badge>
          <h3 className="line-clamp-1 text-title-m text-on-surface">{title}</h3>
          {meta ? (
            <p className="line-clamp-1 text-body-s text-on-surface-variant">{meta}</p>
          ) : null}
          <div className="mt-1 flex items-center justify-between gap-2">
            <span className="text-title-m text-on-surface">{price}</span>
            <Button size="sm" onClick={onAction}>
              {ctaLabel ?? t.cta}
            </Button>
          </div>
        </div>
      </div>
    );
  },
);
MonetizableItem.displayName = "MonetizableItem";
