import type { Meta, StoryObj } from "@storybook/nextjs";
import { StatItem } from "@/components/ui/stat-item";

const meta = {
  title: "Data/StatItem",
  component: StatItem,
  parameters: { layout: "padded" },
  argTypes: {
    label: { control: "text" },
    value: { control: "text" },
    delta: { control: "text" },
    trend: { control: "inline-radio", options: ["up", "down", "flat"] },
    note: { control: "text" },
  },
  args: { label: "이번 달 후원", value: "₩1,240,000", delta: "+12.4%", trend: "up" },
} satisfies Meta<typeof StatItem>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const Dashboard: Story = {
  name: "대시보드 요약",
  render: () => (
    <div className="grid w-[32rem] max-w-full grid-cols-3 gap-4 rounded-lg border border-outline p-4">
      <StatItem label="팔로워" value="12.4k" delta="+320" trend="up" />
      <StatItem label="이번 달 후원" value="₩1.24M" delta="-4.1%" trend="down" />
      <StatItem label="정산 예정" value="₩980,000" note="※ 수수료 확정 전 추정치" />
    </div>
  ),
};
