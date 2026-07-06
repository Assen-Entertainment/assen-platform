import type { Meta, StoryObj } from "@storybook/nextjs";
import { DataTable, type DataTableColumn } from "@/components/ui/data-table";
import { StatusChip } from "@/components/ui/status-chip";

interface Order {
  id: string;
  product: string;
  amount: string;
  status: "완료" | "대기" | "취소";
}

const columns: DataTableColumn<Order>[] = [
  { key: "id", header: "주문번호" },
  { key: "product", header: "상품" },
  { key: "amount", header: "금액", align: "right" },
  {
    key: "status",
    header: "상태",
    render: (r) => (
      <StatusChip variant={r.status === "완료" ? "success" : r.status === "취소" ? "danger" : "neutral"}>
        {r.status}
      </StatusChip>
    ),
  },
];

const rows: Order[] = [
  { id: "ORD-1001", product: "봄 한정 아트북", amount: "₩24,000", status: "완료" },
  { id: "ORD-1002", product: "아크릴 스탠드", amount: "₩13,000", status: "대기" },
  { id: "ORD-1003", product: "디지털 월페이퍼", amount: "₩5,000", status: "취소" },
];

const meta = {
  title: "Data/DataTable",
  component: DataTable,
  parameters: { layout: "padded" },
} satisfies Meta<typeof DataTable>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <div className="w-[40rem] max-w-full">
      <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} caption="주문 목록" />
    </div>
  ),
};

export const Loading: Story = {
  name: "로딩",
  render: () => (
    <div className="w-[40rem] max-w-full">
      <DataTable columns={columns} rows={[]} rowKey={(r) => r.id} loading caption="주문 목록" />
    </div>
  ),
};

export const Empty: Story = {
  name: "빈 상태",
  render: () => (
    <div className="w-[40rem] max-w-full">
      <DataTable columns={columns} rows={[]} rowKey={(r) => r.id} caption="주문 목록" />
    </div>
  ),
};
