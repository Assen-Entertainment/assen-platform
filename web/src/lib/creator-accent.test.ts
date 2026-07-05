import { describe, it, expect } from "vitest";
import {
  hexToRgb, contrastRatio, ensureContrast, creatorAccentVars, creatorAccentFromBase, hoverShift, bestOn, AA_TEXT,
} from "@/lib/creator-accent";

describe("creator-accent (WCAG)", () => {
  it("hexToRgb parses #fff/#000", () => {
    expect(hexToRgb("#ffffff")).toEqual({ r: 255, g: 255, b: 255 });
    expect(hexToRgb("#000")).toEqual({ r: 0, g: 0, b: 0 });
  });

  it("hexToRgb guards invalid input (no NaN)", () => {
    const c = hexToRgb("not-a-color");
    expect(Number.isNaN(c.r)).toBe(false);
  });

  it("contrastRatio black/white ≈ 21", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 0);
  });

  it("ensureContrast reaches the target ratio", () => {
    const fixed = ensureContrast("#999999", "#ffffff", AA_TEXT);
    expect(contrastRatio(fixed, "#ffffff")).toBeGreaterThanOrEqual(AA_TEXT - 0.05);
  });

  it("creatorAccentVars: on-accent meets UI contrast(≥3) vs accent", () => {
    const v = creatorAccentVars("#E14B8A") as Record<string, string>;
    expect(v["--creator-accent"]).toBeTruthy();
    expect(v["--on-creator-accent"]).toBeTruthy();
    expect(contrastRatio(v["--on-creator-accent"], v["--creator-accent"])).toBeGreaterThanOrEqual(3);
  });
});

describe("filled hover 색조 시프트 (ASS-163)", () => {
  // 정적 primary hover 토큰(build-tokens 산출값). onPrimary=흰색 대비 AA(≥4.5) 유지.
  const PRIMARY_HOVER = "#3727ed";
  it("primary hover 토큰이 흰(onPrimary) 텍스트 AA(≥4.5)를 만족한다", () => {
    expect(contrastRatio(PRIMARY_HOVER, "#ffffff")).toBeGreaterThanOrEqual(4.5);
  });

  it("hoverShift는 텍스트에서 멀어지는 방향이라 대비가 감소하지 않는다(어두운 accent)", () => {
    const accent = "#5A4DF0"; // onAccent=흰색
    const hover = hoverShift(accent, bestOn(accent));
    expect(contrastRatio(hover, bestOn(accent))).toBeGreaterThanOrEqual(contrastRatio(accent, bestOn(accent)));
  });

  it("hoverShift는 밝은 accent(검은 텍스트)에서도 대비를 유지한다", () => {
    const accent = "#FFD54A"; // onAccent=검정
    const hover = hoverShift(accent, bestOn(accent));
    expect(contrastRatio(hover, bestOn(accent))).toBeGreaterThanOrEqual(contrastRatio(accent, bestOn(accent)));
  });

  it("creatorAccentVars가 --creator-accent-hover를 함께 방출한다", () => {
    const v = creatorAccentVars("#E14B8A") as Record<string, string>;
    expect(v["--creator-accent-hover"]).toBeTruthy();
    expect(v["--creator-accent-hover"]).not.toBe(v["--creator-accent"]);
  });

  it("creatorAccentFromBase.accentHover가 accent와 다른 톤이다", () => {
    const a = creatorAccentFromBase("#5A4DF0");
    expect(a.accentHover).toBeTruthy();
    expect(a.accentHover).not.toBe(a.accent);
  });
});
