/**
 * 결정적 커버 폴백 아트 — 실 이미지 자산 게이트 전까지 "빈 타일"을 프리미엄하게 채운다.
 *
 * [R14 미니멀 럭셔리] 예전의 채도 높은 멀티-휴 그라디언트(무지개 벽)를 폐기하고,
 * 저채도 톤(tonal) 시스템으로 전환한다: surface 토큰을 브랜드로 아주 미세하게 틴트한
 * "프리미엄 페이퍼 / 소프트 스톤" 표면 + 초저강도 그레인 텍스처 + 절제된 모노그램.
 *
 * 유지(감사 호평 항목):
 *  - 결정적(seed→항상 같은 아트), CLS 0(컨테이너 aspect 예약), 외부 URL 0(CSP·오프라인 안전).
 *  - 오버레이 텍스트/이니셜 대비는 소비 측 토큰으로 보장(WCAG).
 * 개선:
 *  - 색은 CSS color-mix + 토큰 참조 → 라이트/다크 자동 추종(예전엔 색이 baked 되어 다크 무시).
 *  - seed 는 색상(hue)이 아니라 톤/광원/각도를 미세하게 흔든다 → 타일이 "조용히" 달라진다(무지개 아님).
 */
import type { CSSProperties } from "react";
import { ensureContrast, AA_TEXT } from "@/lib/creator-accent";

/** 문자열 → 0..359 hue. djb2 변형, 결정적. 빈 문자열은 0. (avatarTone 파생용으로 유지) */
export function hueFromSeed(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = (h * 31 + seed.charCodeAt(i)) % 360;
  }
  return ((h % 360) + 360) % 360;
}

/** hex(#rrggbb) → 0..359 hue. (외부 호환 유지용 순수 유틸.) */
export function hexToHue(hex: string): number {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex.trim());
  if (!m) return 0;
  const r = parseInt(m[1] ?? "0", 16) / 255, g = parseInt(m[2] ?? "0", 16) / 255, b = parseInt(m[3] ?? "0", 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  if (d === 0) return 0;
  let h: number;
  if (max === r) h = ((g - b) / d) % 6;
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;
  return ((Math.round(h * 60) % 360) + 360) % 360;
}

/**
 * seed + salt → 0..1 결정적 유닛값. FNV-1a(32bit, Math.imul).
 * 톤/광원/각도 파생용 — 서로 독립된 축이라 같은 seed 라도 축마다 다른 값이 나온다.
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
 * 정적 그레인 텍스처(SVG feTurbulence) data-URI. 커버 폴백·히어로 표면에 초저강도로 얹어
 * "디자인된 표면"(플랫 CSS 그라디언트 아님)으로 읽히게 한다. 색 없음(grayscale)이라
 * 라이트/다크 모두에서 중립. 타일링(stitch)·140px·외부 URL 0.
 */
export const COVER_GRAIN_URI: string = (() => {
  const svg =
    `<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'>` +
    `<filter id='n'>` +
    `<feTurbulence type='fractalNoise' baseFrequency='0.82' numOctaves='2' stitchTiles='stitch'/>` +
    `<feColorMatrix type='saturate' values='0'/>` +
    `<feComponentTransfer><feFuncA type='linear' slope='0.85'/></feComponentTransfer>` +
    `</filter>` +
    `<rect width='140' height='140' filter='url(#n)'/>` +
    `</svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
})();

/**
 * seed → 저채도 톤 커버 표면 스타일(라이트/다크 토큰 추종).
 *
 * 3층 합성(전부 토큰·color-mix → 테마 반응):
 *  1) linear tone — surface 계열 두 톤 사이 미세 대각 그라디언트(각도 seed 파생).
 *  2) radial glow — 브랜드(또는 tintVar)로 아주 옅은 하이라이트(광원 위치 seed 파생).
 *  3) grain      — soft-light 로 얹은 그레인(질감).
 * tintVar: 틴트 색(기본 브랜드 --primary). 크리에이터 카드는 var(--creator-accent) 주입 →
 * "크리에이터가 색이 된다"를 조용히(저채도) 유지.
 */
export function coverFallbackStyle(seed: string, tintVar = "var(--primary)"): CSSProperties {
  // 결정적 파생 — 색상(hue)이 아니라 톤 강도·광원·각도만 흔든다(무지개 방지, 조용한 차별).
  const angle = Math.round(seedUnit(seed, 1) * 120 + 100); // 100..220deg
  const lx = Math.round(14 + seedUnit(seed, 2) * 64); // 14..78%
  const ly = Math.round(6 + seedUnit(seed, 3) * 34); //  6..40%
  const cA = (4 + seedUnit(seed, 4) * 5).toFixed(1); // 4.0..9.0% 브랜드 틴트(상단)
  const cB = (2 + seedUnit(seed, 5) * 4).toFixed(1); // 2.0..6.0% 브랜드 틴트(하단)
  const cGlow = (8 + seedUnit(seed, 6) * 8).toFixed(1); // 8.0..16.0% 하이라이트(투명 위라 실질 옅음)

  const toneA = `color-mix(in oklab, ${tintVar} ${cA}%, var(--surface-container-high))`;
  const toneB = `color-mix(in oklab, ${tintVar} ${cB}%, var(--surface-container))`;
  const glow = `color-mix(in oklab, ${tintVar} ${cGlow}%, transparent)`;

  return {
    backgroundColor: toneA, // color-mix 미지원 브라우저 폴백(무채색 근처 → 절대 컬러 박스/흰 플래시 없음)
    backgroundImage: [
      `url("${COVER_GRAIN_URI}")`,
      `radial-gradient(120% 120% at ${lx}% ${ly}%, ${glow} 0%, transparent 55%)`,
      `linear-gradient(${angle}deg, ${toneA} 0%, ${toneB} 100%)`,
    ].join(", "),
    backgroundSize: "140px 140px, 100% 100%, 100% 100%",
    backgroundRepeat: "repeat, no-repeat, no-repeat",
    backgroundPosition: "0 0, center, center",
    backgroundBlendMode: "soft-light, normal, normal",
  } as CSSProperties;
}

/**
 * [하위호환] 기존 호출부(feed·post·media-viewer·creator 커버 등)가 쓰던 이름.
 * 이제 저채도 톤 커버 스타일을 반환한다(예전 멀티-휴 그라디언트 → 미니멀 럭셔리 톤).
 * 두 번째 인자(baseHue)는 더 이상 색을 바꾸지 않는다(톤 시스템은 색상 회전을 쓰지 않음) — 시그니처만 유지.
 */
export function gradientStyle(seed: string, _baseHue?: number): CSSProperties {
  return coverFallbackStyle(seed);
}

/** seed → 커버 모노그램 이니셜. 서로게이트/한글 안전(Array.from). 라틴은 대문자화. */
export function initialFor(seed: string): string {
  const t = (seed ?? "").trim();
  if (!t) return "";
  const first = Array.from(t)[0] ?? "";
  return first.toUpperCase();
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
 * (아바타는 작은 원형 액센트라 톤 시스템과 별개로 채도 있는 이니셜 유지 — 감사 호평 대비 로직 보존.)
 */
export function avatarTone(seed: string): AvatarTone {
  const hue = hueFromSeed(seed);
  const base = hslHex(hue, 0.5, 0.45);
  return { bg: ensureContrast(base, "#ffffff", AA_TEXT), fg: "#ffffff" };
}
