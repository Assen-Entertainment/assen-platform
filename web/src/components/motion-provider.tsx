"use client";
import * as React from "react";
import { MotionConfig, LazyMotion, domAnimation } from "framer-motion";

/**
 * MotionProvider — framer-motion 전역 설정(대표 피드백 #8 a11y 가드 + 번들 최적화).
 * reducedMotion="user": OS의 prefers-reduced-motion을 존중해 이동/스케일 등 transform 애니메이션을
 * 자동 비활성화하고 페이드(opacity)만 남긴다. framer-motion은 JS 구동이라 CSS 미디어쿼리 가드가
 * 닿지 않으므로 이 설정이 리치 모션의 접근성 준수를 보장한다.
 * LazyMotion(domAnimation) — 풀피처 `motion`(drag/layout 포함) 대신 경량 `m` + domAnimation
 * 피처 번들만 로드한다. motion-primitives.tsx(Reveal/Stagger/StaggerItem)는 opacity+transform만
 * 쓰므로 domAnimation으로 충분 — 전 라우트 상주 번들 크기를 줄인다.
 */
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      <LazyMotion features={domAnimation}>{children}</LazyMotion>
    </MotionConfig>
  );
}
