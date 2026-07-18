import type { Meta, StoryObj } from "@storybook/nextjs";
import { Divider } from "@/components/ui/divider";

const meta = {
  title: "Primitives/Divider",
  component: Divider,
  parameters: { layout: "centered" },
  argTypes: {
    orientation: { control: "inline-radio", options: ["horizontal", "vertical"] },
  },
} satisfies Meta<typeof Divider>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Horizontal: Story = {
  render: () => (
    <div className="w-64">
      <p className="text-body-s text-on-surface">위</p>
      <Divider className="my-3" />
      <p className="text-body-s text-on-surface">아래</p>
    </div>
  ),
};

export const Vertical: Story = {
  render: () => (
    <div className="flex h-10 items-center gap-3 text-body-s text-on-surface">
      <span>왼쪽</span>
      <Divider orientation="vertical" />
      <span>오른쪽</span>
    </div>
  ),
};
