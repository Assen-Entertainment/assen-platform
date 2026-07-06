import type { Meta, StoryObj } from "@storybook/nextjs";
import { Tag } from "@/components/ui/tag";

const meta = {
  title: "Primitives/Tag",
  component: Tag,
  parameters: { layout: "centered" },
  argTypes: {
    children: { control: "text" },
  },
  args: { children: "한정판" },
} satisfies Meta<typeof Tag>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const Group: Story = {
  name: "태그 묶음",
  render: () => (
    <div className="flex flex-wrap items-center gap-1.5">
      <Tag>일러스트</Tag>
      <Tag>디지털</Tag>
      <Tag>한정 100개</Tag>
      <Tag>선주문</Tag>
    </div>
  ),
};
