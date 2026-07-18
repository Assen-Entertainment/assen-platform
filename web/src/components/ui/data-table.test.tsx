import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataTable, type DataTableColumn } from "@/components/ui/data-table";

interface Row {
  id: string;
  name: string;
  qty: number;
}

const columns: DataTableColumn<Row>[] = [
  { key: "name", header: "이름" },
  { key: "qty", header: "수량", align: "right", render: (r) => <span>{r.qty}개</span> },
];

const rows: Row[] = [
  { id: "a", name: "굿즈", qty: 3 },
  { id: "b", name: "티켓", qty: 5 },
];

describe("DataTable", () => {
  it("renders rows (Default state)", () => {
    render(<DataTable columns={columns} rows={rows} rowKey={(r) => r.id} />);
    expect(screen.getByText("굿즈")).toBeInTheDocument();
    expect(screen.getByText("3개")).toBeInTheDocument();
    // 컬럼 헤더는 th(scope=col)로 렌더.
    expect(screen.getByRole("columnheader", { name: "이름" })).toBeInTheDocument();
  });

  it("renders empty state when there are no rows", () => {
    render(<DataTable columns={columns} rows={[]} rowKey={(r) => r.id} />);
    expect(screen.getByText("표시할 항목이 없어요")).toBeInTheDocument();
    expect(screen.queryByText("굿즈")).not.toBeInTheDocument();
  });

  it("renders loading skeletons instead of data", () => {
    const { container } = render(
      <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} loading loadingRows={3} />,
    );
    // 로딩 중에는 실제 데이터를 렌더하지 않는다.
    expect(screen.queryByText("굿즈")).not.toBeInTheDocument();
    // 스켈레톤 = aria-hidden 톤 샤인 블록(P3: animate-pulse → skeleton-shimmer).
    expect(container.querySelectorAll(".skeleton-shimmer").length).toBeGreaterThan(0);
  });
});
