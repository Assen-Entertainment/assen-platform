import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReportSheet } from "@/components/ui/report-sheet";

describe("ReportSheet", () => {
  it("disables submit until a reason is chosen, then submits the payload", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const onOpenChange = vi.fn();
    render(<ReportSheet open onOpenChange={onOpenChange} onSubmit={onSubmit} />);

    const submit = screen.getByRole("button", { name: "신고 제출" });
    expect(submit).toBeDisabled();

    // 사유 라디오 선택(서버 FAN_REPORTABLE_TYPES 정렬 — unwanted_request).
    await user.click(screen.getByLabelText("원치 않는 요구·부담"));
    expect(submit).toBeEnabled();

    await user.click(submit);
    expect(onSubmit).toHaveBeenCalledWith({ reason: "unwanted_request", detail: "" });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
