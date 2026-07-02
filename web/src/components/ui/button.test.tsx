import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders children", () => {
    render(<Button>확인</Button>);
    expect(screen.getByRole("button", { name: "확인" })).toBeInTheDocument();
  });

  it("applies outline variant class", () => {
    render(<Button variant="outline">a</Button>);
    expect(screen.getByRole("button")).toHaveClass("border");
  });

  it("asChild renders an anchor", () => {
    render(
      <Button asChild>
        <a href="/x">link</a>
      </Button>,
    );
    expect(screen.getByRole("link", { name: "link" })).toHaveAttribute("href", "/x");
  });
});
