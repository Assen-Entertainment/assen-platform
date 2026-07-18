"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * MediaImage — 실 미디어 URL 렌더링(Codex #18). 크리에이터가 업로드한 실 이미지 URL이 있으면
 * <img>로, 없거나 로드 실패면 기존 seed 그라디언트 플레이스홀더로 폴백(시각 회귀 0).
 * 임의 URL(크리에이터 업로드, 어떤 호스트든 가능)을 다루므로 next/image가 아닌
 * plain img + lazy + onError 폴백을 쓴다(remote-image 설정 불필요).
 * overlay(성인/잠금/품절 배지 등)는 children으로 넘겨 기존과 동일하게 미디어 위에 컴포지트한다.
 */
export function MediaImage({
  src,
  alt,
  gradientStyle,
  className,
  imgClassName,
  children,
}: {
  src?: string | null;
  alt: string;
  gradientStyle?: React.CSSProperties; // caller passes the same var(--gradient-brand)/accent it used before
  className?: string;
  imgClassName?: string;
  children?: React.ReactNode;
}) {
  const [failed, setFailed] = React.useState(false);
  const showImg = Boolean(src) && !failed;
  return (
    <div className={cn("relative overflow-hidden", className)} style={showImg ? undefined : gradientStyle}>
      {showImg ? (
        // eslint-disable-next-line @next/next/no-img-element -- 임의 크리에이터 업로드 URL(원격 최적화 불가), smart-image.tsx와 동일 패턴.
        <img
          src={src as string}
          alt={alt}
          loading="lazy"
          onError={() => setFailed(true)}
          className={cn("h-full w-full object-cover", imgClassName)}
        />
      ) : null}
      {children}
    </div>
  );
}
