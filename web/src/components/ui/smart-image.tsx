"use client";
import * as React from "react";
import NextImage from "next/image";
import { cn } from "@/lib/utils";

/**
 * SmartImage — Avatar·CreatorThumbCard의 `imageComponent` 슬롯에 주입하는 이미지 래퍼(R5-W3 #6).
 * 실 원격 URL(http/https)이면 next/image(fill·sizes 최적화), 그 외(data:·상대·미지정)는 원시 <img>.
 * next/image는 fill 모드 → 부모가 relative + 크기 확정이어야 한다(Avatar/ThumbCard 컨테이너가 보장).
 * 그라디언트 placeholder 경로(src 미지정)는 이 컴포넌트를 타지 않는다 → 무영향.
 */
export function isRemoteImage(src?: string): boolean {
  return typeof src === "string" && /^https?:\/\//i.test(src);
}

export interface SmartImageProps {
  src?: string;
  alt?: string;
  className?: string;
  /** 반응형 소스 힌트 — next/image 최적화용. 미지정 시 보수적 기본값. */
  sizes?: string;
  loading?: "lazy" | "eager";
  onError?: React.ReactEventHandler<HTMLImageElement>;
}

export function SmartImage({
  src,
  alt = "",
  className,
  sizes = "(max-width: 768px) 100vw, 33vw",
  loading = "lazy",
  onError,
}: SmartImageProps) {
  if (!isRemoteImage(src)) {
    // 최적화 비대상(data:/상대/미지정) — 원시 img.
    // eslint-disable-next-line @next/next/no-img-element -- 비원격 소스는 next/image 최적화 불가.
    return <img src={src} alt={alt} loading={loading} className={className} onError={onError} />;
  }
  return (
    <NextImage
      src={src as string}
      alt={alt}
      fill
      sizes={sizes}
      className={cn("object-cover", className)}
      onError={onError}
    />
  );
}
