import * as React from "react";
import { cn } from "@/lib/utils";
import { creatorAccentVars } from "@/lib/creator-accent";

/**
 * CreatorThumbCard — Figma DS(31:7). 디스커버리 크리에이터 카드.
 * [브랜드 루브릭] C 크리에이터 표현: 이름 강조 + accentColor 주입 시 커버가 크리에이터 색("크리에이터가 색이 된다").
 *  B 시그니처: 커버 폴백 gradient.brand. A craft: hover scale. ※Figma 원본 fs12·회색 → 상향(Figma 동기 권고).
 */
export interface CreatorThumbCardProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  name: string;
  meta?: string; // "모델 · 팔로워 1.2k"
  cover?: string;
  /** 이 크리에이터의 시그니처 색(hex). 주입 시 커버가 creator-accent(자동 대비 파생). */
  accentColor?: string;
}

export const CreatorThumbCard = React.forwardRef<HTMLAnchorElement, CreatorThumbCardProps>(
  ({ name, meta, cover, accentColor, className, style, ...props }, ref) => (
    <a
      ref={ref}
      style={accentColor ? { ...creatorAccentVars(accentColor), ...style } : style}
      className={cn("group flex flex-col gap-1.5", className)}
      {...props}
    >
      <div
        className="aspect-square w-full overflow-hidden rounded-md bg-surface-container-high"
        style={
          cover
            ? undefined
            : accentColor
              ? { backgroundColor: "var(--creator-accent)" }
              : { backgroundImage: "var(--gradient-brand)" }
        }
      >
        {cover ? (
          // eslint-disable-next-line @next/next/no-img-element -- DS 이식성 위해 원시 img(소비자가 next/image 래핑 가능)
          <img
            src={cover}
            alt={name}
            loading="lazy"
            className="size-full object-cover transition-transform duration-200 group-hover:scale-[1.03] motion-reduce:transition-none"
          />
        ) : null}
      </div>
      <span className="line-clamp-1 text-title-m text-on-surface">{name}</span>
      {meta ? <span className="line-clamp-1 text-caption text-on-surface-variant">{meta}</span> : null}
    </a>
  ),
);
CreatorThumbCard.displayName = "CreatorThumbCard";
