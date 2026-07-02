import { describe, it, expect } from "vitest";
import { hexToRgb, contrastRatio, ensureContrast, creatorAccentVars, AA_TEXT } from "@/lib/creator-accent";

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
