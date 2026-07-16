import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { emitVerifyRequired } from "@/lib/verify-gate";
import { VerifyGate } from "./verify-gate";

// next/navigation — jsdom 렌더용 경량 목(라우팅 부수효과 제거).
const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
  usePathname: () => "/creator/stellar",
}));

describe("VerifyGate", () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  it("최초에는 다이얼로그가 닫혀 있다", () => {
    render(<VerifyGate />);
    expect(screen.queryByText("본인인증이 필요해요")).toBeNull();
  });

  it("emitVerifyRequired 신호를 받으면 다이얼로그가 열린다", () => {
    render(<VerifyGate />);
    act(() => emitVerifyRequired());
    expect(screen.getByText("본인인증이 필요해요")).toBeInTheDocument();
  });

  it("본인인증하기를 누르면 /verify?next=<현재경로>로 이동한다", () => {
    render(<VerifyGate />);
    act(() => emitVerifyRequired());
    act(() => screen.getByRole("button", { name: "본인인증하기" }).click());
    expect(pushMock).toHaveBeenCalledWith(`/verify?next=${encodeURIComponent("/creator/stellar")}`);
  });
});
