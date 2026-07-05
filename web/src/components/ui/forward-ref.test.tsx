import { describe, it, expect } from "vitest";
import * as React from "react";
import { render } from "@testing-library/react";
import { Spinner } from "@/components/ui/spinner";
import { Skeleton } from "@/components/ui/skeleton";
import { Divider } from "@/components/ui/divider";
import { PriceLabel } from "@/components/ui/price-label";

/** ASS-162 — DS 원자 컴포넌트 forwardRef 스윕: ref 전달 + displayName 일관성. */
describe("forwardRef 스윕 (ASS-162)", () => {
  it("Spinner가 <svg> 에 ref를 전달한다", () => {
    const ref = React.createRef<SVGSVGElement>();
    render(<Spinner ref={ref} />);
    expect(ref.current).toBeInstanceOf(SVGSVGElement);
    expect(ref.current?.getAttribute("role")).toBe("status");
  });

  it("Skeleton이 <div> 에 ref를 전달한다", () => {
    const ref = React.createRef<HTMLDivElement>();
    render(<Skeleton ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLDivElement);
  });

  it("Divider가 <div> 에 ref를 전달한다", () => {
    const ref = React.createRef<HTMLDivElement>();
    render(<Divider ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLDivElement);
    expect(ref.current?.getAttribute("role")).toBe("separator");
  });

  it("PriceLabel이 <span> 에 ref를 전달한다", () => {
    const ref = React.createRef<HTMLSpanElement>();
    render(<PriceLabel ref={ref} amount={9900} />);
    expect(ref.current).toBeInstanceOf(HTMLSpanElement);
  });

  it("displayName 이 설정되어 있다", () => {
    expect(Spinner.displayName).toBe("Spinner");
    expect(Skeleton.displayName).toBe("Skeleton");
    expect(Divider.displayName).toBe("Divider");
    expect(PriceLabel.displayName).toBe("PriceLabel");
  });
});
