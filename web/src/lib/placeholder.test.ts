import { describe, it, expect } from "vitest";
import {
  hueFromSeed,
  coverFallbackStyle,
  gradientStyle,
  initialFor,
  COVER_GRAIN_URI,
  avatarTone,
  AVATAR_TONE_PALETTE,
} from "@/lib/placeholder";
import { contrastRatio } from "@/lib/creator-accent";

describe("placeholder", () => {
  it("hueFromSeed is deterministic and within 0..359", () => {
    expect(hueFromSeed("stellar")).toBe(hueFromSeed("stellar"));
    for (const s of ["", "a", "토끼방송국", "p1", "별빛 일러스트"]) {
      const h = hueFromSeed(s);
      expect(h).toBeGreaterThanOrEqual(0);
      expect(h).toBeLessThan(360);
      expect(Number.isInteger(h)).toBe(true);
    }
  });

  it("COVER_GRAIN_URI is an encoded svg data-uri (no raw markup, no external url)", () => {
    expect(COVER_GRAIN_URI.startsWith("data:image/svg+xml,")).toBe(true);
    // filter id 참조는 %23 로 인코딩되어야 배경 URL 로 안전.
    expect(COVER_GRAIN_URI).toContain("%23n");
    expect(COVER_GRAIN_URI).not.toContain("<svg"); // 원시 꺾쇠는 인코딩됨
    // 외부 리소스 참조 0(CSP 안전) — xmlns 네임스페이스(http://www.w3.org/...)는 네트워크 요청이 아님.
    expect(COVER_GRAIN_URI).not.toContain("xlink:href");
    expect(COVER_GRAIN_URI).not.toMatch(/url\(https?:/i);
  });

  it("coverFallbackStyle is deterministic, token-based, and grain-layered", () => {
    const style = coverFallbackStyle("p1");
    const bg = String(style.backgroundImage);
    // 톤은 surface 토큰을 브랜드로 미세 틴트(color-mix) → 라이트/다크 자동 추종.
    expect(bg).toContain("color-mix");
    expect(bg).toContain("var(--surface-container-high)");
    expect(bg).toContain("var(--primary)");
    // 그레인 텍스처가 최상단 레이어로 합성됨.
    expect(bg).toContain(COVER_GRAIN_URI);
    expect(style.backgroundBlendMode).toContain("soft-light");
    // 결정적.
    expect(String(coverFallbackStyle("p1").backgroundImage)).toBe(bg);
  });

  it("coverFallbackStyle differs quietly per seed (tone/light/angle, not hue)", () => {
    expect(String(coverFallbackStyle("goods").backgroundImage)).not.toBe(
      String(coverFallbackStyle("digital").backgroundImage),
    );
  });

  it("coverFallbackStyle honors a custom tint var (creator accent)", () => {
    const bg = String(coverFallbackStyle("neon", "var(--creator-accent)").backgroundImage);
    expect(bg).toContain("var(--creator-accent)");
    expect(bg).not.toContain("var(--primary)");
  });

  it("gradientStyle is a back-compat alias of coverFallbackStyle", () => {
    expect(String(gradientStyle("p1").backgroundImage)).toBe(
      String(coverFallbackStyle("p1").backgroundImage),
    );
  });

  it("initialFor returns a deterministic, surrogate-safe monogram", () => {
    expect(initialFor("neonbeats")).toBe("N");
    expect(initialFor("  space  ")).toBe("S");
    expect(initialFor("별빛 일러스트")).toBe("별");
    expect(initialFor("")).toBe("");
    expect(initialFor("😺 cat")).toBe("😺");
  });

  it("avatarTone background meets AA (>=4.5:1) against white text", () => {
    for (const s of ["나", "별빛 일러스트", "neonbeats", "z"]) {
      const { bg, fg } = avatarTone(s);
      expect(fg).toBe("#ffffff");
      expect(contrastRatio(bg, fg)).toBeGreaterThanOrEqual(4.5);
    }
    expect(avatarTone("나").bg).toBe(avatarTone("나").bg);
  });

  it("avatarTone stays inside the curated brand-family palette (no hue rotation / rainbow)", () => {
    // 무지개 회귀 방지 — 어떤 seed 든 배경은 반드시 큐레이션 팔레트의 한 색이어야 한다.
    // (전 톤이 이미 AA 통과 딥 톤이라 ensureContrast 가 원색을 그대로 반환.)
    const palette = new Set<string>(AVATAR_TONE_PALETTE);
    for (const s of ["stellar", "rabbit", "neonbeats", "myo", "lumi", "c1", "c2", "나", "z", "a", ""]) {
      expect(palette.has(avatarTone(s).bg)).toBe(true);
    }
    // 팔레트는 브랜드 인디고 앵커를 포함하고, 절제된 5톤(무지개 아님)으로 유지한다.
    expect(AVATAR_TONE_PALETTE).toContain("#4b3fcb");
    expect(AVATAR_TONE_PALETTE.length).toBeLessThanOrEqual(6);
    // 각 큐레이션 톤 자체도 흰 텍스트와 AA 를 만족(팔레트 정의 불변식).
    for (const c of AVATAR_TONE_PALETTE) {
      expect(contrastRatio(c, "#ffffff")).toBeGreaterThanOrEqual(4.5);
    }
  });
});
