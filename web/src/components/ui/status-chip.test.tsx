import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusChip } from "@/components/ui/status-chip";

describe("StatusChip", () => {
  it("success 변형은 success-container 토큰을 사용한다", () => {
    render(<StatusChip variant="success">완료</StatusChip>);
    const el = screen.getByText("완료");
    expect(el).toBeInTheDocument();
    expect(el).toHaveClass("bg-success-container");
  });

  it("danger 변형은 error-container 토큰을 사용한다", () => {
    render(<StatusChip variant="danger">거절</StatusChip>);
    expect(screen.getByText("거절")).toHaveClass("bg-error-container");
  });

  it("dot=false 면 상태 점을 렌더하지 않는다", () => {
    const { container: off } = render(<StatusChip variant="info" dot={false}>진행</StatusChip>);
    expect(off.querySelector('[aria-hidden="true"]')).toBeNull();
    const { container: on } = render(<StatusChip variant="info">진행</StatusChip>);
    expect(on.querySelector('[aria-hidden="true"]')).not.toBeNull();
  });
});
