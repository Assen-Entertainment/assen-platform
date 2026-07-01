import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";

describe("Badge", () => {
  it("renders success variant with container token", () => {
    render(<Badge variant="success">완료</Badge>);
    const el = screen.getByText("완료");
    expect(el).toBeInTheDocument();
    expect(el).toHaveClass("bg-success-container");
  });
});
