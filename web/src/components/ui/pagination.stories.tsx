import * as React from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { Pagination } from "@/components/ui/pagination";

const meta = {
  title: "Navigation/Pagination",
  component: Pagination,
  parameters: { layout: "centered" },
} satisfies Meta<typeof Pagination>;

export default meta;
type Story = StoryObj<typeof meta>;

function PaginationDemo({ total }: { total: number }) {
  const [page, setPage] = React.useState(1);
  return <Pagination page={page} total={total} onPage={setPage} />;
}

export const Short: Story = {
  name: "짧은 목록(<=7)",
  render: () => <PaginationDemo total={5} />,
};

export const Long: Story = {
  name: "긴 목록(생략)",
  render: () => <PaginationDemo total={24} />,
};
