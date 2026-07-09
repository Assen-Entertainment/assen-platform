"use client";
// 리치 모션 프리미티브(대표 피드백 #8) — framer-motion 기반 스크롤 리빌·스태거·마이크로 인터랙션.
// ⚠️ framer-motion은 JS(Web Animations/rAF) 구동이라 globals.css의 CSS prefers-reduced-motion
//    가드가 적용되지 않는다. 접근성은 앱 루트의 <MotionConfig reducedMotion="user">가 담당한다
//    (모션 프로바이더). reduced-motion 사용자에게는 이동(transform)이 제거되고 페이드만 남는다.
// ⚡ 번들 최적화 — 풀피처 `motion` 대신 경량 `m` + LazyMotion(domAnimation)을 쓴다. Reveal/Stagger는
//    opacity+transform(whileInView/whileHover)만 사용해 domAnimation으로 충분(drag/layout 불필요).
//    LazyMotion 경계는 앱 루트(MotionProvider)가 제공 — 이 프리미티브는 `m`만 소비한다.
import * as React from "react";
import { m, type Variants } from "framer-motion";

/** 앱 CSS 토큰(cubic-bezier(0,0,0.2,1))과 동일 계열의 부드러운 감속 이징. */
export const EASE_OUT = [0.16, 1, 0.3, 1] as const;

const fadeUpVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE_OUT } },
};

const containerVariants: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.02 } },
};

/** Reveal — 뷰포트 진입 시 1회 페이드+상승. 스크롤 트리거 섹션 리빌용. */
export function Reveal({
  children,
  className,
  delay = 0,
  y = 16,
  amount = 0.2,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  y?: number;
  amount?: number;
}) {
  return (
    <m.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount }}
      transition={{ duration: 0.5, ease: EASE_OUT, delay }}
    >
      {children}
    </m.div>
  );
}

/** Stagger — 자식 StaggerItem을 순차 진입시키는 컨테이너. className으로 그리드/플렉스 레이아웃 유지. */
export function Stagger({
  children,
  className,
  amount = 0.12,
}: {
  children: React.ReactNode;
  className?: string;
  amount?: number;
}) {
  return (
    <m.div
      className={className}
      variants={containerVariants}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, amount }}
    >
      {children}
    </m.div>
  );
}

/** StaggerItem — Stagger의 자식. lift=true면 hover 시 살짝 떠오르는 마이크로 인터랙션. */
export function StaggerItem({
  children,
  className,
  lift = false,
}: {
  children: React.ReactNode;
  className?: string;
  lift?: boolean;
}) {
  return (
    <m.div
      className={className}
      variants={fadeUpVariants}
      whileHover={lift ? { y: -4 } : undefined}
      transition={{ duration: 0.2, ease: EASE_OUT }}
    >
      {children}
    </m.div>
  );
}
