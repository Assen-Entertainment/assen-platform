/**
 * 결정적 플레이스홀더 아트 — 실 이미지 자산 게이트 전까지 "회색 박스"를 제거한다.
 *
 * 문자열 seed(제목·핸들·id) → 안정적인 hue → SVG 그라디언트 data-URI(cover/미디어) 또는
 * 대비 보정된 아바타 톤(이니셜 배경색)을 생성한다. 외부 URL 없음(오프라인/CSP 안전),
 * 순수 함수(단위 테스트 대상). 같은 seed는 항상 같은 색을 낸다.
 */
import type { CSSProperties } from "react";
import { ensureContrast, AA_TEXT } from "@/lib/creator-accent";

/** 문자열 → 0..359 hue. djb2 변형, 결정적. 빈 문자열은 0. */
export function hueFromSeed(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = (h * 31 + seed.charCodeAt(i)) % 360;
  }
  return ((h % 360) + 360) % 360;
}

/** HSL(0..1 s/l) → hex. 아바타 톤 대비 보정 입력용. */
function hslHex(h: number, s: number, l: number): string {
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let r = 0, g = 0, b = 0;
  if (h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  const hex = (v: number) => Math.round((v + m) * 255).toString(16).padStart(2, "0");
  return `#${hex(r)}${hex(g)}${hex(b)}`;
}

/**
 * seed → SVG 그라디언트 data-URI. cover/포스트·상품 미디어의 배경으로 사용.
 * preserveAspectRatio=none 으로 컨테이너를 꽉 채운다(background-size: cover 와 병행).
 */
export function gradientDataUri(seed: string): string {
  const h1 = hueFromSeed(seed);
  const h2 = (h1 + 40) % 360;
  const svg =
    `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' preserveAspectRatio='none'>` +
    `<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>` +
    `<stop offset='0' stop-color='hsl(${h1},62%,60%)'/>` +
    `<stop offset='1' stop-color='hsl(${h2},64%,46%)'/>` +
    `</linearGradient></defs>` +
    `<rect width='100' height='100' fill='url(#g)'/></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

/** style={} 에 펼쳐 미디어 컨테이너 배경으로. 종횡비는 컨테이너(aspect-*)가 예약 → CLS 0. */
export function gradientStyle(seed: string): CSSProperties {
  return {
    backgroundImage: `url("${gradientDataUri(seed)}")`,
    backgroundSize: "cover",
    backgroundPosition: "center",
  };
}

export interface AvatarTone {
  /** 배경색(hex) — WCAG AA(4.5:1)로 흰 텍스트 대비 보정됨. */
  bg: string;
  /** 전경(이니셜) 색. */
  fg: string;
}

/**
 * seed → 아바타 배경 톤. hue 파생색을 흰 텍스트와 4.5:1 이상이 되도록 어둡게 보정.
 * 이니셜 텍스트는 소비 측(Avatar)이 렌더 → 회색 대신 크리에이터별 파생색.
 */
export function avatarTone(seed: string): AvatarTone {
  const hue = hueFromSeed(seed);
  const base = hslHex(hue, 0.5, 0.45);
  return { bg: ensureContrast(base, "#ffffff", AA_TEXT), fg: "#ffffff" };
}
