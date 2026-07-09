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

/** hex(#rrggbb) → 0..359 hue. 크리에이터 accent를 메쉬 base hue로 쓸 때(색은 유지, 리치니스 부여). */
export function hexToHue(hex: string): number {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex.trim());
  if (!m) return 0;
  const r = parseInt(m[1], 16) / 255, g = parseInt(m[2], 16) / 255, b = parseInt(m[3], 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  if (d === 0) return 0;
  let h: number;
  if (max === r) h = ((g - b) / d) % 6;
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;
  return ((Math.round(h * 60) % 360) + 360) % 360;
}

/**
 * seed + salt → 0..1 결정적 유닛값. FNV-1a(32bit, Math.imul) — 그라디언트 광원 위치 파생용.
 * hue와 독립된 축이라 같은 색이라도 seed마다 광원 배치가 달라져 "메쉬"가 반복되지 않는다.
 */
function seedUnit(seed: string, salt: number): number {
  let h = (0x811c9dc5 ^ salt) >>> 0;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return ((h >>> 0) % 1000) / 1000;
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
 * seed → SVG 메쉬 그라디언트 data-URI. cover/포스트·상품 미디어의 배경으로 사용.
 * preserveAspectRatio=none 으로 컨테이너를 꽉 채운다(background-size: cover 와 병행).
 *
 * 단색 대각 채움 대신 3층 합성으로 깊이를 준다(플랫 박스 → "디자인된" 아트):
 *  1) base   — 대각 linear(id='g'). seed hue → 인접 hue(+38°) 2-stop.
 *  2) glow    — 밝은 radial 하이라이트(광원). seed 파생 위치라 카드마다 다른 구도.
 *  3) deep    — 어두운 radial(대각 반대편)로 대비·부피감.
 * 전부 seed 결정적·순수·오프라인(외부 URL 0). 같은 seed = 항상 같은 아트.
 */
export function gradientDataUri(seed: string, baseHue?: number): string {
  const h1 = baseHue ?? hueFromSeed(seed);
  const h2 = (h1 + 38) % 360; // 인접색(대각 그라디언트 끝)
  const h3 = (h1 + 340) % 360; // -20°, 반대편 톤 → 메쉬 다색감
  // 광원 위치(%) — hue와 독립된 축이라 색이 겹쳐도 구도가 반복되지 않는다.
  const ax = Math.round(12 + seedUnit(seed, 1) * 46); // 12..58 (상단 하이라이트)
  const ay = Math.round(8 + seedUnit(seed, 2) * 34); //  8..42
  const bx = Math.round(46 + seedUnit(seed, 3) * 46); // 46..92 (하단 딥)
  const by = Math.round(58 + seedUnit(seed, 4) * 34); // 58..92
  const svg =
    `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' preserveAspectRatio='none'>` +
    `<defs>` +
    `<linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>` +
    `<stop offset='0' stop-color='hsl(${h1},58%,57%)'/>` +
    `<stop offset='1' stop-color='hsl(${h2},62%,42%)'/>` +
    `</linearGradient>` +
    `<radialGradient id='a' cx='${ax}%' cy='${ay}%' r='62%'>` +
    `<stop offset='0' stop-color='hsl(${h3},78%,70%)' stop-opacity='0.85'/>` +
    `<stop offset='1' stop-color='hsl(${h3},78%,70%)' stop-opacity='0'/>` +
    `</radialGradient>` +
    `<radialGradient id='b' cx='${bx}%' cy='${by}%' r='55%'>` +
    `<stop offset='0' stop-color='hsl(${h1},74%,32%)' stop-opacity='0.55'/>` +
    `<stop offset='1' stop-color='hsl(${h1},74%,32%)' stop-opacity='0'/>` +
    `</radialGradient>` +
    `</defs>` +
    `<rect width='100' height='100' fill='url(#g)'/>` +
    `<rect width='100' height='100' fill='url(#a)'/>` +
    `<rect width='100' height='100' fill='url(#b)'/>` +
    `</svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

/** style={} 에 펼쳐 미디어 컨테이너 배경으로. 종횡비는 컨테이너(aspect-*)가 예약 → CLS 0. */
export function gradientStyle(seed: string, baseHue?: number): CSSProperties {
  return {
    backgroundImage: `url("${gradientDataUri(seed, baseHue)}")`,
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
