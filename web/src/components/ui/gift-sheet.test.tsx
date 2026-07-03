import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GiftSheet } from "@/components/ui/gift-sheet";

describe("GiftSheet", () => {
  it("gifts a preset amount and shows the completion delight", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    render(<GiftSheet open onOpenChange={() => {}} creatorName="별빛" onComplete={onComplete} />);

    // 기본 프리셋(3,000)이 선택되어 후원하기 활성.
    const submit = screen.getByRole("button", { name: /후원하기/ });
    await user.click(submit);

    expect(onComplete).toHaveBeenCalledWith(3000, "");
    expect(screen.getByText("후원해 주셔서 고마워요!")).toBeInTheDocument();
    expect(screen.getByText(/별빛님에게 ₩3,000/)).toBeInTheDocument();
  });

  it("uses the custom amount over the preset when entered", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    render(<GiftSheet open onOpenChange={() => {}} creatorName="토끼" onComplete={onComplete} />);

    await user.type(screen.getByLabelText("직접 입력"), "7000");
    await user.click(screen.getByRole("button", { name: /₩7,000 후원하기/ }));

    expect(onComplete).toHaveBeenCalledWith(7000, "");
  });
});
