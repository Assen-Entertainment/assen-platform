import type { Meta, StoryObj } from "@storybook/nextjs";
import { Badge } from "@/components/ui/badge";

const meta = {
  title: "Primitives/Badge",
  component: Badge,
  parameters: { layout: "centered" },
  argTypes: {
    variant: {
      control: "inline-radio",
      options: ["neutral", "primary", "success", "warning", "error"],
    },
    children: { control: "text" },
  },
  args: { children: "라벨", variant: "neutral" },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <Badge variant="neutral">중립</Badge>
      <Badge variant="primary">인기</Badge>
      <Badge variant="success">완료</Badge>
      <Badge variant="warning">대기</Badge>
      <Badge variant="error">취소</Badge>
    </div>
  ),
};
