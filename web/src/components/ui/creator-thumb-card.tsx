import * as React from "react";
import { cn } from "@/lib/utils";
import { creatorAccentVars } from "@/lib/creator-accent";
import { CoverFallback } from "@/components/ui/cover-fallback";

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
  /**
   * 커버 이미지 렌더 슬롯(R5-W3 #6) — 기본 "img"(DS 이식성). SmartImage 등 next/image 래퍼 주입 가능.
   * fill 주입을 위해 커버 컨테이너는 relative + 크기 확정.
   */
  imageComponent?: React.ElementType;
  /** next/image 슬롯 주입 시 반응형 힌트. */
  sizes?: string;
}

export const CreatorThumbCard = React.forwardRef<HTMLAnchorElement, CreatorThumbCardProps>(
  ({ name, meta, cover, accentColor, imageComponent, sizes, className, style, ...props }, ref) => {
    const ImageComp = imageComponent ?? "img";
    return (
    <a
      ref={ref}
      style={accentColor ? { ...creatorAccentVars(accentColor), ...style } : style}
      className={cn("group flex flex-col gap-2", className)}
      {...props}
    >
      {/* 미디어 타일 — 헤어라인(ring)은 이미지/톤 커버 위에서도 동작. hover 소프트 그림자(shadow-2)로 카드 시스템과 정렬. */}
      <div className="relative aspect-square w-full overflow-hidden rounded-lg bg-surface-container-high shadow-1 ring-1 ring-inset ring-on-surface/10 transition-shadow duration-200 group-hover:shadow-2 motion-reduce:transition-none">
        {cover ? (
          <ImageComp
            src={cover}
            alt={name}
            loading="lazy"
            sizes={sizes}
            className="size-full object-cover transition-transform duration-300 ease-out group-hover:scale-[1.05] motion-reduce:transition-none"
          />
        ) : (
          // 이미지 없음 → 프리미엄 톤 커버 + 크리에이터 이니셜 모노그램. accentColor 주입 시
          // creatorAccentVars 스코프의 --creator-accent 로 조용히 틴트("크리에이터가 색이 된다").
          <CoverFallback seed={name} tintVar={accentColor ? "var(--creator-accent)" : undefined} />
        )}
        {/* 하단 스크림 — hover 시 깊이/가독성. gradient·이미지 커버 공통. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-black/25 to-transparent opacity-0 transition-opacity duration-200 group-hover:opacity-100 motion-reduce:transition-none"
        />
      </div>
      <div className="flex flex-col gap-0.5 px-0.5">
        <span className="line-clamp-1 text-title-m text-on-surface transition-colors group-hover:text-primary motion-reduce:transition-none">
          {name}
        </span>
        {meta ? <span className="line-clamp-1 text-caption text-on-surface-variant">{meta}</span> : null}
      </div>
    </a>
    );
  },
);
CreatorThumbCard.displayName = "CreatorThumbCard";
