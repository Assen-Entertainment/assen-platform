import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MediaViewer } from "@/components/ui/media-viewer";

describe("MediaViewer", () => {
  it("does not render when closed", () => {
    render(<MediaViewer open={false} onClose={() => {}} seed="po1" />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders an accessible modal dialog when open", () => {
    render(<MediaViewer open onClose={() => {}} seed="po1" caption="캡션" alt="포스트 미디어" />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("캡션")).toBeInTheDocument();
  });

  it("closes on Escape key", () => {
    const onClose = vi.fn();
    render(<MediaViewer open onClose={onClose} seed="po1" />);
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes on backdrop click but not on content click", () => {
    const onClose = vi.fn();
    render(<MediaViewer open onClose={onClose} seed="po1" alt="미디어" />);
    // 콘텐츠(미디어) 클릭은 전파 차단 → 닫히지 않음.
    fireEvent.click(screen.getByRole("img", { name: "미디어" }));
    expect(onClose).not.toHaveBeenCalled();
    // 배경(dialog) 클릭 → 닫힘.
    fireEvent.click(screen.getByRole("dialog"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("keeps focus trapped on Tab (single control)", () => {
    render(<MediaViewer open onClose={() => {}} seed="po1" />);
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Tab" });
    expect(screen.getByRole("button", { name: "닫기" })).toHaveFocus();
  });
});
