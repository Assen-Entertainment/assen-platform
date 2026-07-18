import * as React from "react";
import { cn } from "@/lib/utils";
import { coverFallbackStyle, initialFor } from "@/lib/placeholder";

/**
 * CoverFallback — 실 이미지가 없을 때의 프리미엄 커버 폴백(R14 미니멀 럭셔리).
 *
 * 저채도 톤 표면(coverFallbackStyle) + 절제된 모노그램. 예전 "무지개 그라디언트 벽"을
 * "의도된·프리미엄·차분한" 빈 커버로 대체한다. 부모는 relative + 크기 확정이어야 한다
 * (타일 컨테이너는 이미 aspect-* 로 예약 → CLS 0).
 *
 * - seed: 결정적 톤/모노그램 시드(이름·제목·id). 같은 seed = 항상 같은 커버.
 * - tintVar: 톤 틴트 색(기본 브랜드 --primary). 크리에이터 카드는 "var(--creator-accent)" 주입.
 * - label: 모노그램 문자 오버라이드(기본 seed 이니셜).
 * - monogram: false 면 톤 표면만(배너 등).
 *
 * 모노그램은 SVG <text fill=currentColor> 라 컨테이너에 꽉 맞춰 스케일(해상도 독립)되고
 * text-on-surface-variant 로 라이트/다크 자동 추종한다. on-surface-variant 는 톤 베이스 대비
 * 라이트/다크 모두 ≥3:1(WCAG AA 대형 텍스트) — 저대비이되 판독 가능. 순수 장식이라 aria-hidden.
 */
export function CoverFallback({
  seed,
  tintVar,
  label,
  monogram = true,
  className,
}: {
  seed: string;
  tintVar?: string;
  label?: string;
  monogram?: boolean;
  className?: string;
}) {
  const ch = (label ?? initialFor(seed)) || "";
  return (
    <div
      aria-hidden
      className={cn("absolute inset-0 h-full w-full", className)}
      style={coverFallbackStyle(seed, tintVar)}
    >
      {monogram && ch ? (
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="xMidYMid meet"
          className="absolute inset-0 h-full w-full text-on-surface-variant"
        >
          <text
            x="50"
            y="52"
            textAnchor="middle"
            dominantBaseline="central"
            fill="currentColor"
            fontSize="40"
            fontWeight={300}
            letterSpacing="-1.5"
            style={{ fontFamily: "var(--font-sans)" }}
          >
            {ch}
          </text>
        </svg>
      ) : null}
    </div>
  );
}
