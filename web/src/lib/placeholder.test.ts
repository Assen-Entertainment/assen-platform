import { describe, it, expect } from "vitest";
import { hueFromSeed, gradientDataUri, gradientStyle, avatarTone } from "@/lib/placeholder";
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

  it("different seeds generally yield different hues", () => {
    expect(hueFromSeed("goods")).not.toBe(hueFromSeed("digital"));
  });

  it("gradientDataUri returns an encoded svg data-uri (deterministic)", () => {
    const uri = gradientDataUri("adorable");
    expect(uri.startsWith("data:image/svg+xml,")).toBe(true);
    // '#g' 참조는 %23 로 인코딩되어야 배경 URL 로 안전.
    expect(uri).toContain("%23g");
    expect(uri).not.toContain("<svg"); // 원시 꺾쇠는 인코딩됨
    expect(gradientDataUri("adorable")).toBe(uri);
  });

  it("gradientStyle exposes a cover background-image", () => {
    const style = gradientStyle("p1");
    expect(style.backgroundSize).toBe("cover");
    expect(String(style.backgroundImage)).toContain("data:image/svg+xml,");
  });

  it("avatarTone background meets AA (>=4.5:1) against white text", () => {
    for (const s of ["나", "별빛 일러스트", "neonbeats", "z"]) {
      const { bg, fg } = avatarTone(s);
      expect(fg).toBe("#ffffff");
      expect(contrastRatio(bg, fg)).toBeGreaterThanOrEqual(4.5);
    }
    expect(avatarTone("나").bg).toBe(avatarTone("나").bg);
  });
});
