import type { Meta, StoryObj } from "@storybook/nextjs";
import { StatusChip } from "@/components/ui/status-chip";

const meta = {
  title: "Primitives/StatusChip",
  component: StatusChip,
  parameters: { layout: "centered" },
  argTypes: {
    variant: {
      control: "inline-radio",
      options: ["neutral", "info", "success", "danger"],
    },
    dot: { control: "boolean" },
    children: { control: "text" },
  },
  args: { children: "결제 대기", variant: "neutral", dot: true },
} satisfies Meta<typeof StatusChip>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const AllVariants: Story = {
  name: "상태 전체",
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <StatusChip variant="neutral">대기</StatusChip>
      <StatusChip variant="info">진행중</StatusChip>
      <StatusChip variant="success">완료</StatusChip>
      <StatusChip variant="danger">실패</StatusChip>
    </div>
  ),
};

export const WithoutDot: Story = {
  name: "점 없음",
  args: { dot: false, variant: "success", children: "정산 완료" },
};
