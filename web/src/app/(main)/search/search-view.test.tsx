import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SearchView } from "./search-view";
import type { Creator, Product } from "@/lib/api";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
}));

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const creators: Creator[] = [
  { id: "c1", name: "별빛 일러스트", handle: "stellar", followers: 100, category: "일러스트" },
];
const products: Product[] = [{ id: "p1", type: "goods", title: "아크릴 스탠드", price: 18000 }];

const RECENT_KEY = "assen.recentSearches";
function seedRecent(list: string[]) {
  localStorage.setItem(RECENT_KEY, JSON.stringify(list));
}
function readRecent(): string[] {
  return JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]");
}

function view() {
  return <SearchView creators={creators} products={products} />;
}

describe("SearchView 서제스트 상호작용", () => {
  beforeEach(() => {
    pushMock.mockReset();
    localStorage.clear();
  });

  it("최근 검색어를 드롭다운에 노출하고 항목 클릭 시 검색으로 이동한다", () => {
    seedRecent(["토끼", "네온"]);
    wrap(view());
    const input = screen.getByRole("combobox");
    fireEvent.focus(input);

    expect(screen.getByText("최근 검색어")).toBeInTheDocument();
    fireEvent.click(screen.getByText("토끼"));
    expect(pushMock).toHaveBeenCalledWith(`/search?q=${encodeURIComponent("토끼")}`);
  });

  it("키보드 ↑↓/Enter로 최근 검색어를 선택한다", () => {
    seedRecent(["토끼", "네온"]);
    wrap(view());
    const input = screen.getByRole("combobox");
    fireEvent.focus(input);

    fireEvent.keyDown(input, { key: "ArrowDown" }); // highlight 0 (토끼)
    fireEvent.keyDown(input, { key: "ArrowDown" }); // highlight 1 (네온)
    fireEvent.keyDown(input, { key: "ArrowUp" }); // highlight 0 (토끼)
    fireEvent.keyDown(input, { key: "Enter" });
    expect(pushMock).toHaveBeenCalledWith(`/search?q=${encodeURIComponent("토끼")}`);
  });

  it("Escape로 드롭다운을 닫는다", () => {
    seedRecent(["토끼"]);
    wrap(view());
    const input = screen.getByRole("combobox");
    fireEvent.focus(input);
    expect(screen.getByText("최근 검색어")).toBeInTheDocument();

    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByText("최근 검색어")).not.toBeInTheDocument();
  });

  it("최근 검색어를 개별 삭제하고 전체 삭제한다", () => {
    seedRecent(["토끼", "네온"]);
    wrap(view());
    const input = screen.getByRole("combobox");
    fireEvent.focus(input);

    // 개별 삭제 — "토끼"만 사라지고 localStorage도 갱신.
    fireEvent.click(screen.getByLabelText("토끼 삭제"));
    expect(screen.queryByText("토끼")).not.toBeInTheDocument();
    expect(screen.getByText("네온")).toBeInTheDocument();
    expect(readRecent()).toEqual(["네온"]);

    // 전체 삭제 — 목록 비고 드롭다운 닫힘.
    fireEvent.click(screen.getByText("전체 삭제"));
    expect(screen.queryByText("네온")).not.toBeInTheDocument();
    expect(readRecent()).toEqual([]);
  });

  it("질의 입력 시 서제스트를 노출하고 항목 클릭 시 크리에이터로 이동한다", async () => {
    wrap(view());
    const input = screen.getByRole("combobox");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "별빛" } });

    // 디바운스(250ms) 후 서제스트(listbox)에 크리에이터가 노출된다(mock /search).
    // ※크리에이터명은 하단 결과 목록에도 있어 드롭다운(listbox)으로 스코프한다.
    await waitFor(() =>
      expect(within(screen.getByRole("listbox")).getByText("별빛 일러스트")).toBeInTheDocument(),
    );

    fireEvent.click(within(screen.getByRole("listbox")).getByText("별빛 일러스트"));
    expect(pushMock).toHaveBeenCalledWith("/creator/stellar");
  });

  it("서제스트의 '전체 결과 보기'를 Enter로 실행한다", async () => {
    wrap(view());
    const input = screen.getByRole("combobox");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "별빛" } });

    await waitFor(() =>
      expect(within(screen.getByRole("listbox")).getByText("별빛 일러스트")).toBeInTheDocument(),
    );

    // 마지막 옵션("전체 결과 보기")까지 내려가 Enter → 전체 검색 이동.
    fireEvent.keyDown(input, { key: "ArrowDown" }); // 크리에이터
    fireEvent.keyDown(input, { key: "ArrowDown" }); // 전체 결과 보기
    fireEvent.keyDown(input, { key: "Enter" });
    expect(pushMock).toHaveBeenCalledWith(`/search?q=${encodeURIComponent("별빛")}`);
  });
});
