"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { avatarTone } from "@/lib/placeholder";

/** Avatar — Figma DS Avatar(12:8). 이미지/이니셜 폴백 + 사이즈 + 인증 뱃지. (Radix Avatar로 업그레이드 가능) */
const SIZES = {
  sm: "size-8 text-caption",
  md: "size-10 text-label",
  lg: "size-14 text-title-m",
  xl: "size-24 text-display-m",
} as const;

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string;
  alt?: string;
  fallback?: string;
  size?: keyof typeof SIZES;
  verified?: boolean;
  /** seed(핸들·이름 등) — 이미지 없을 때 회색 대신 결정적 파생색 배경(대비 보정). */
  tone?: string;
  /**
   * 이미지 렌더 슬롯(R5-W3 #6) — 기본 "img"(DS 이식성). 소비처에서 next/image 래퍼(SmartImage) 주입 가능.
   * fill 기반 컴포넌트를 주입할 수 있도록 이미지 컨테이너는 relative + 크기 확정.
   */
  imageComponent?: React.ElementType;
  /** next/image 슬롯 주입 시 반응형 힌트. */
  sizes?: string;
}

export const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(
  ({ src, alt, fallback, size = "md", verified, tone, imageComponent, sizes, className, ...props }, ref) => {
    const [errored, setErrored] = React.useState(false);
    const showImg = src && !errored;
    const toneColors = !showImg && tone ? avatarTone(tone) : null;
    const ImageComp = imageComponent ?? "img";
    return (
      <div ref={ref} className={cn("relative inline-flex shrink-0", className)} {...props}>
        <div
          className={cn(
            "relative flex items-center justify-center overflow-hidden rounded-full font-medium",
            toneColors ? "" : "bg-surface-container-high text-on-surface-variant",
            SIZES[size],
          )}
          style={toneColors ? { backgroundColor: toneColors.bg, color: toneColors.fg } : undefined}
        >
          {showImg ? (
            <ImageComp
              src={src}
              alt={alt ?? ""}
              loading="lazy"
              sizes={sizes}
              className="size-full object-cover"
              onError={() => setErrored(true)}
            />
          ) : (
            <span>{fallback}</span>
          )}
        </div>
        {verified ? (
          <span role="img" aria-label="인증됨" className="absolute -bottom-0.5 -right-0.5 flex size-4 items-center justify-center rounded-full border-2 border-surface bg-primary text-on-primary">
            <svg viewBox="0 0 24 24" className="size-2.5" fill="none" stroke="currentColor" strokeWidth={3}>
              <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
        ) : null}
      </div>
    );
  },
);
Avatar.displayName = "Avatar";
