import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Logo — Assen 브랜드 로크업(플레이스홀더).
 *
 * ⚠️ PLACEHOLDER — 최종 브랜딩(E9) 확정 시 이 컴포넌트만 교체하면 셸·로그인·OG 전역이 갱신된다.
 * 텍스트 <span>Assen</span> 하드코딩을 대체(단일 진실원). 정식 로고 확정 전 임시 워드마크.
 *
 * [디자인 근거 · 크리에이터-커머스]
 *  - 마크: 상승하는 "A" 봉우리(무대/정점으로 오르는 크리에이터) — 파비콘(app/icon.svg)의 A 모노그램과
 *    형태를 공유해 시각 일관. gradient.brand(인디고→바이올렛) 타일로 시그니처 컬러를 담되, 문자는
 *    currentColor 흰색 스트로크 → 라이트/다크 무변. `mono`면 타일 없이 currentColor 단색(칩/푸터용).
 *  - 워드마크: Pretendard, tracking 타이트(-0.02em), 편집형 위계. currentColor 상속 → 양모드 자동 대응.
 *  - 토큰만 사용(--gradient-brand). 색 아이덴티티 불변(발전형 폴리시 가드레일).
 */
export interface LogoProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** full=마크+워드마크(기본), mark=마크만(콤팩트), wordmark=글자만. */
  variant?: "full" | "mark" | "wordmark";
  size?: "sm" | "md" | "lg";
  /** 단색(gradient 타일 제거) — 색 배경/모노 컨텍스트용. 마크가 currentColor를 상속. */
  mono?: boolean;
  /** 접근성 라벨(기본 "Assen"). 마크 단독일 때 특히 중요. */
  label?: string;
}

const MARK_PX = { sm: 22, md: 26, lg: 34 } as const;
const WORD_CLS = {
  sm: "text-title-m",
  md: "text-title-l",
  lg: "text-display-m",
} as const;

/** A 봉우리 모노그램 — 파비콘과 형태 공유(상승하는 A). stroke=currentColor. */
function AssenMark({ px, mono }: { px: number; mono?: boolean }) {
  const stroke = (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      style={{ width: mono ? px : Math.round(px * 0.62), height: mono ? px : Math.round(px * 0.62) }}
    >
      <path d="M10 23 L16 8.5 L22 23 M12.6 17.6 H19.4" />
    </svg>
  );
  if (mono) return stroke;
  return (
    <span
      aria-hidden
      className="grid shrink-0 place-items-center rounded-[28%] text-white shadow-1"
      style={{ width: px, height: px, backgroundImage: "var(--gradient-brand)" }}
    >
      {stroke}
    </span>
  );
}

export const Logo = React.forwardRef<HTMLSpanElement, LogoProps>(
  ({ variant = "full", size = "md", mono, label = "Assen", className, ...props }, ref) => {
    const px = MARK_PX[size];
    return (
      <span
        ref={ref}
        role="img"
        aria-label={label}
        className={cn("inline-flex select-none items-center gap-2 leading-none", className)}
        {...props}
      >
        {variant !== "wordmark" ? <AssenMark px={px} mono={mono} /> : null}
        {variant !== "mark" ? (
          <span
            aria-hidden
            className={cn("font-semibold tracking-[-0.02em]", WORD_CLS[size])}
          >
            Assen
          </span>
        ) : null}
      </span>
    );
  },
);
Logo.displayName = "Logo";
