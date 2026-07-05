import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { SmartImage, isRemoteImage } from "./smart-image";

// next/image를 마커 img로 모킹 — 원격 분기 진입을 data-nextimage로 식별.
vi.mock("next/image", () => ({
  default: ({ src, alt, className }: { src: string; alt: string; className?: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img data-nextimage="1" src={src} alt={alt} className={className} />
  ),
}));

/** R5-W3 #6 — SmartImage 원격/비원격 분기. */
describe("isRemoteImage", () => {
  it("http/https URL만 원격으로 판정한다", () => {
    expect(isRemoteImage("https://cdn.example.com/a.png")).toBe(true);
    expect(isRemoteImage("http://example.com/a.png")).toBe(true);
  });
  it("data:·상대·미지정은 비원격", () => {
    expect(isRemoteImage("data:image/svg+xml,foo")).toBe(false);
    expect(isRemoteImage("/local/a.png")).toBe(false);
    expect(isRemoteImage("./a.png")).toBe(false);
    expect(isRemoteImage(undefined)).toBe(false);
    expect(isRemoteImage("")).toBe(false);
  });
});

describe("SmartImage", () => {
  it("원격 URL이면 next/image 분기(fill 최적화)로 렌더한다", () => {
    const { container } = render(<SmartImage src="https://cdn.example.com/a.png" alt="원격" />);
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img?.getAttribute("data-nextimage")).toBe("1");
    expect(img?.getAttribute("alt")).toBe("원격");
  });

  it("data-uri 소스는 원시 img로 렌더한다(next/image 미사용)", () => {
    const { container } = render(<SmartImage src="data:image/svg+xml,foo" alt="로컬" />);
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img?.getAttribute("data-nextimage")).toBeNull();
    expect(img?.getAttribute("src")).toBe("data:image/svg+xml,foo");
  });

  it("src 미지정도 원시 img 분기(placeholder 경로 무영향)", () => {
    const { container } = render(<SmartImage alt="" />);
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img?.getAttribute("data-nextimage")).toBeNull();
  });
});
