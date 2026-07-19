"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion";

/**
 * ConnectionGlow — Assen 브랜드 시그니처("연결 글로우").
 *
 * 팬↔크리에이터의 연결(팔로우·구독·후원)이 성사되는 순간, 크리에이터 액센트 색의 부드러운
 * 방사형 블룸이 액션 지점에서 "번졌다 잦아드는 숨"으로 1회 재생된다. 세 순간은 서로 다른
 * 효과가 아니라 이 **하나의 프리미티브**를 깊이(depth)로 스케일한다 — 반지름·강도·지속만 달라진다:
 *   follow    = 가장 연하고 빠른 숨
 *   subscribe = 중간
 *   support   = 가장 따뜻(넓고 밝고 길게)하되 여전히 barely-there
 *
 * 색 = var(--creator-accent)(상위 creatorAccentVars 스코프), 폴백 = 브랜드 인디고 #5A4DF0.
 * 라이트/다크 양쪽에서 읽힌다(액센트가 표면 대비 보정된 값이므로).
 *
 * 접근성: 순수 장식(aria-hidden·pointer-events-none). 텍스트 위가 아니라 액션 요소 뒤로 깔려
 * 대비를 떨어뜨리지 않는다. reduced-motion에서는 방사/스케일 없이 **정적 소프트 틴트**만 잠깐
 * 유지 후 사라진다(동일한 onDone 계약). 레이아웃 무관(absolute)이라 CLS 0.
 *
 * 배치: `position: relative`(+되도록 `isolate`) 컨테이너 안에 액션 요소의 형제로 넣는다.
 * 글로우는 컨테이너 중심에서 바깥으로 커지며 요소보다 크므로 부모에 overflow-hidden 금지.
 */
export type ConnectionDepth = "follow" | "subscribe" | "support";

/** 깊이별 파라미터 — size(지름 px)·peak(최대 불투명도)·ms(지속). 모두 모션 예산 ≤ 900ms.
 *  size는 액션 요소(버튼/체크)를 넉넉히 감싸 코어가 요소 뒤에 가려도 바깥 헤일로가 또렷이 번지도록
 *  잡는다. peak는 짧은 인/아웃(26%에서 정점 → 소멸)이라 "조용한 빛의 숨"으로 읽히는 값. */
const DEPTH: Record<ConnectionDepth, { size: number; peak: number; ms: number }> = {
  follow: { size: 220, peak: 0.5, ms: 620 },
  subscribe: { size: 280, peak: 0.58, ms: 760 },
  support: { size: 340, peak: 0.66, ms: 880 },
};

/** reduced-motion 정적 틴트가 화면에 머무는 시간(방사 없이 부드럽게 인지되도록). */
const REDUCED_HOLD_MS = 440;

export interface ConnectionGlowProps {
  /** true가 되는 순간 글로우를 1회 재생한다. onDone에서 false로 되돌리는 one-shot 패턴. */
  show: boolean;
  depth?: ConnectionDepth;
  /** 재생 종료(또는 reduced 유지 종료) 후 호출 — 보통 show를 false로 되돌린다. */
  onDone?: () => void;
  className?: string;
}

const GLOW_GRADIENT =
  "radial-gradient(circle," +
  " color-mix(in srgb, var(--creator-accent, #5a4df0) 78%, transparent) 0%," +
  " color-mix(in srgb, var(--creator-accent, #5a4df0) 48%, transparent) 40%," +
  " color-mix(in srgb, var(--creator-accent, #5a4df0) 18%, transparent) 60%," +
  " transparent 78%)";

export function ConnectionGlow({ show, depth = "follow", onDone, className }: ConnectionGlowProps) {
  const reduced = usePrefersReducedMotion();
  const { size, peak, ms } = DEPTH[depth];

  // onDone은 렌더마다 바뀔 수 있으므로 ref로 최신값을 잡아 타이머 재설정을 피한다.
  const onDoneRef = React.useRef(onDone);
  onDoneRef.current = onDone;

  React.useEffect(() => {
    if (!show) return;
    const hold = reduced ? REDUCED_HOLD_MS : ms;
    const t = setTimeout(() => onDoneRef.current?.(), hold);
    return () => clearTimeout(t);
  }, [show, reduced, ms]);

  if (!show) return null;

  return (
    <span
      aria-hidden
      data-connection-glow={depth}
      className={cn(
        "pointer-events-none absolute left-1/2 top-1/2 z-0 rounded-full",
        className,
      )}
      style={{
        width: size,
        height: size,
        background: GLOW_GRADIENT,
        ...(reduced
          ? // 정적 소프트 틴트 — 방사/스케일 없음. 강도는 살짝 낮춰 잔잔하게.
            { opacity: Math.min(peak, 0.26), transform: "translate(-50%, -50%) scale(1)" }
          : {
              opacity: 0,
              transform: "translate(-50%, -50%) scale(0.4)",
              animation: `connection-glow ${ms}ms cubic-bezier(0.22, 0.61, 0.36, 1) forwards`,
              // 키프레임이 var(--glow-peak)로 최대 불투명도를 읽는다.
              ["--glow-peak" as string]: String(peak),
            }),
      }}
    />
  );
}
