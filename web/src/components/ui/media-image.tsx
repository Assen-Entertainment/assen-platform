"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { CoverFallback } from "@/components/ui/cover-fallback";

/**
 * MediaImage — 실 미디어 URL 렌더링(Codex #18). 크리에이터가 업로드한 실 이미지 URL이 있으면
 * <img>로, 없거나 로드 실패면 프리미엄 커버 폴백으로 폴백(R14: 저채도 톤 + 모노그램).
 * 임의 URL(크리에이터 업로드, 어떤 호스트든 가능)을 다루므로 next/image가 아닌
 * plain img + lazy + onError 폴백을 쓴다(remote-image 설정 불필요).
 * overlay(성인/잠금/품절 배지 등)는 children으로 넘겨 기존과 동일하게 미디어 위에 컴포지트한다.
 *
 * 폴백 선택:
 *  - seed 제공 → <CoverFallback>(톤 표면 + 모노그램). 엔티티 타일(상품·크리에이터 등)에 권장.
 *  - seed 없이 gradientStyle 만 → 해당 배경 스타일 사용(배너·포스트 미디어 등, 모노그램 없음).
 */
export function MediaImage({
  src,
  alt,
  gradientStyle,
  seed,
  tintVar,
  monogram = true,
  className,
  imgClassName,
  children,
}: {
  src?: string | null;
  alt: string;
  /** seed 없이 톤/브랜드 배경만 필요할 때(배너 등). caller 가 넘긴 배경 스타일을 그대로 쓴다. */
  gradientStyle?: React.CSSProperties;
  /** 프리미엄 커버 폴백 시드(제목·이름·id). 주입 시 톤 표면 + 모노그램 렌더. */
  seed?: string;
  /** 커버 폴백 틴트 색(기본 브랜드). 크리에이터 컨텍스트에서 "var(--creator-accent)". */
  tintVar?: string;
  /** 커버 폴백 모노그램 표시. 와이드 배너(아바타 오버랩)에선 false 로 톤 표면만. 기본 true. */
  monogram?: boolean;
  className?: string;
  imgClassName?: string;
  children?: React.ReactNode;
}) {
  const [failed, setFailed] = React.useState(false);
  const showImg = Boolean(src) && !failed;
  return (
    <div
      className={cn("relative overflow-hidden", className)}
      style={!showImg && !seed ? gradientStyle : undefined}
    >
      {showImg ? (
        // eslint-disable-next-line @next/next/no-img-element -- 임의 크리에이터 업로드 URL(원격 최적화 불가), smart-image.tsx와 동일 패턴.
        <img
          src={src as string}
          alt={alt}
          loading="lazy"
          onError={() => setFailed(true)}
          className={cn("h-full w-full object-cover", imgClassName)}
        />
      ) : seed ? (
        <CoverFallback seed={seed} tintVar={tintVar} monogram={monogram} />
      ) : null}
      {children}
    </div>
  );
}
