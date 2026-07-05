import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import BlockedSettingsPage from "./page";
import { qk } from "@/lib/api/queries";
import type { BlockedCreator } from "@/lib/api";

vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: { href: unknown; children: React.ReactNode }) => (
    <a href={typeof href === "string" ? href : "#"} {...p}>
      {children}
    </a>
  ),
}));

function wrap(qc: QueryClient, ui: React.ReactElement) {
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

// staleTime Infinity → 시드한 목록만으로 렌더(마운트 refetch로 인한 시드 덮어쓰기 방지).
function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
}

describe("BlockedSettingsPage", () => {
  it("차단 목록을 렌더하고 해제 시 항목을 즉시 제거한다(낙관적)", async () => {
    const qc = makeClient();
    qc.setQueryData<BlockedCreator[]>(qk.blocks, [
      { creatorId: "c1", name: "별빛 일러스트", handle: "stellar" },
      { creatorId: "c3", name: "토끼방송국", handle: "rabbit" },
    ]);
    wrap(qc, <BlockedSettingsPage />);

    expect(screen.getByText("별빛 일러스트")).toBeInTheDocument();
    expect(screen.getByText("토끼방송국")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getAllByRole("button", { name: "차단 해제" })[0]);

    await waitFor(() => {
      expect(screen.queryByText("별빛 일러스트")).not.toBeInTheDocument();
    });
    // 나머지 항목은 유지.
    expect(screen.getByText("토끼방송국")).toBeInTheDocument();
  });

  it("빈 목록이면 안내를 보여준다", () => {
    const qc = makeClient();
    qc.setQueryData<BlockedCreator[]>(qk.blocks, []);
    wrap(qc, <BlockedSettingsPage />);
    expect(screen.getByText("차단한 크리에이터가 없어요")).toBeInTheDocument();
  });
});
