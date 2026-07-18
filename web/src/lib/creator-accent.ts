/**
 * 런타임 크리에이터 액센트 — packages/ui_kit/lib/src/creator_accent.dart 의 TS 포트.
 *
 * 크리에이터가 지정한 임의 색(base) 1개에서 WCAG 대비를 만족하는 액센트 셋을 파생한다:
 *  - accent              : surface 위에서 UI 대비(>=3:1)를 만족하도록 보정한 base
 *  - onAccent            : accent 위 텍스트(흑/백 중 대비 큰 쪽)
 *  - accentContainer     : accent 를 surface 에 12% 틴트한 연한 배경
 *  - onAccentContainer   : accentContainer 위 텍스트(AA 4.5:1 까지 명도 보정)
 *
 * 적용: 프로필 헤더 커버·구독/팔로우 CTA·활성 탭·티어 강조 한정. 전역 chrome 은 인디고(primary) 유지.
 * 사용: <div style={creatorAccentVars(creator.themeColor)}> ... bg-creator-accent / text-on-creator-accent ... </div>
 */

import type { CSSProperties } from "react";

export const AA_TEXT = 4.5;
export const AA_UI = 3.0;

type RGB = { r: number; g: number; b: number };

function clamp(n: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, n));
}

export function hexToRgb(hex: string): RGB {
  let h = (hex || "").replace("#", "").trim();
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  if (!/^[0-9a-fA-F]{6}$/.test(h)) h = "5a4df0"; // 잘못된 입력 → primary 폴백(NaN 방지)
  const num = parseInt(h.slice(0, 6), 16);
  return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
}

export function rgbToHex({ r, g, b }: RGB): string {
  const c = (v: number) => Math.round(clamp(v, 0, 255)).toString(16).padStart(2, "0");
  return `#${c(r)}${c(g)}${c(b)}`;
}

/** WCAG 상대 휘도 (0..1). */
function relativeLuminance({ r, g, b }: RGB): number {
  const lin = (v: number) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

/** WCAG 대비비 (1..21). 입력은 hex. */
export function contrastRatio(a: string, b: string): number {
  const la = relativeLuminance(hexToRgb(a));
  const lb = relativeLuminance(hexToRgb(b));
  const [hi, lo] = la >= lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

function rgbToHsl({ r, g, b }: RGB): { h: number; s: number; l: number } {
  const rn = r / 255, gn = g / 255, bn = b / 255;
  const max = Math.max(rn, gn, bn), min = Math.min(rn, gn, bn);
  let h = 0;
  const l = (max + min) / 2;
  const d = max - min;
  const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
  if (d !== 0) {
    switch (max) {
      case rn: h = ((gn - bn) / d) % 6; break;
      case gn: h = (bn - rn) / d + 2; break;
      default: h = (rn - gn) / d + 4;
    }
    h *= 60;
    if (h < 0) h += 360;
  }
  return { h, s, l };
}

function hslToRgb({ h, s, l }: { h: number; s: number; l: number }): RGB {
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let rp = 0, gp = 0, bp = 0;
  if (h < 60) [rp, gp, bp] = [c, x, 0];
  else if (h < 120) [rp, gp, bp] = [x, c, 0];
  else if (h < 180) [rp, gp, bp] = [0, c, x];
  else if (h < 240) [rp, gp, bp] = [0, x, c];
  else if (h < 300) [rp, gp, bp] = [x, 0, c];
  else [rp, gp, bp] = [c, 0, x];
  return { r: (rp + m) * 255, g: (gp + m) * 255, b: (bp + m) * 255 };
}

/** fg 의 명도를 조정해 bg 대비 target 이상이 되도록 보정한 색. */
export function ensureContrast(fg: string, bg: string, target: number): string {
  if (contrastRatio(fg, bg) >= target) return fg;
  const bgLum = relativeLuminance(hexToRgb(bg));
  const darken = bgLum > 0.5; // 밝은 배경 → fg 어둡게
  const { h, s } = rgbToHsl(hexToRgb(fg));
  let best = fg, bestC = contrastRatio(fg, bg);
  for (let i = 1; i <= 100; i++) {
    const l = clamp(darken ? 0.5 - i * 0.005 : 0.5 + i * 0.005);
    const cand = rgbToHex(hslToRgb({ h, s, l }));
    const c = contrastRatio(cand, bg);
    if (c > bestC) { best = cand; bestC = c; }
    if (c >= target) return cand;
  }
  return best; // target 도달 불가 시 최선
}

/** accent 위 텍스트로 흑/백 중 대비 큰 쪽. */
export function bestOn(accent: string): string {
  return contrastRatio("#ffffff", accent) >= contrastRatio("#000000", accent) ? "#ffffff" : "#000000";
}

/**
 * hover 색조 시프트 — 명도를 텍스트(onAccent)와 반대 방향으로 amount 만큼 이동해 톤을 심화한다.
 * 텍스트에서 멀어지는 방향이라 hover 시 텍스트 대비가 (감소하지 않고) 유지·상승 → AA 보존.
 * primary 정적 토큰(indigo.hover, -8% darken)과 같은 언어의 런타임 파생.
 */
export function hoverShift(accent: string, onAccent: string, amount = 0.08): string {
  const { h, s, l } = rgbToHsl(hexToRgb(accent));
  const darken = onAccent === "#ffffff"; // 흰 텍스트(어두운 accent) → 더 어둡게, 검은 텍스트 → 더 밝게
  return rgbToHex(hslToRgb({ h, s, l: clamp(darken ? l - amount : l + amount) }));
}

/** base 색을 surface 에 ratio 만큼 섞기. */
function mix(base: string, surface: string, ratio: number): string {
  const a = hexToRgb(base), b = hexToRgb(surface);
  return rgbToHex({
    r: a.r * ratio + b.r * (1 - ratio),
    g: a.g * ratio + b.g * (1 - ratio),
    b: a.b * ratio + b.b * (1 - ratio),
  });
}

export interface CreatorAccent {
  accent: string;
  accentHover: string;
  onAccent: string;
  accentContainer: string;
  onAccentContainer: string;
}

/** base(크리에이터 지정색) → 대비 보정된 액센트 셋. surface 기본 흰색(라이트). */
export function creatorAccentFromBase(base: string, surface = "#ffffff"): CreatorAccent {
  const accent = ensureContrast(base, surface, AA_UI);
  const accentContainer = mix(base, surface, 0.12);
  const onAccent = bestOn(accent);
  return {
    accent,
    accentHover: hoverShift(accent, onAccent),
    onAccent,
    accentContainer,
    onAccentContainer: ensureContrast(base, accentContainer, AA_TEXT),
  };
}

/** style={} 에 펼쳐 넣을 CSS 변수 객체. base 가 없으면 기본(primary) 유지. */
export function creatorAccentVars(
  base?: string | null,
  surface = "#ffffff",
): CSSProperties {
  if (!base) return {};
  const a = creatorAccentFromBase(base, surface);
  return {
    "--creator-accent": a.accent,
    "--creator-accent-hover": a.accentHover,
    "--on-creator-accent": a.onAccent,
    "--creator-accent-container": a.accentContainer,
    "--on-creator-accent-container": a.onAccentContainer,
  } as CSSProperties;
}
