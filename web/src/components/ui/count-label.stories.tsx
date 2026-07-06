import type { Meta, StoryObj } from "@storybook/nextjs";
import { CountLabel } from "@/components/ui/count-label";

const meta = {
  title: "Primitives/CountLabel",
  component: CountLabel,
  parameters: { layout: "centered" },
  argTypes: {
    count: { control: "number" },
    label: { control: "text" },
    compact: { control: "boolean" },
  },
  args: { count: 12400, label: "팔로워", compact: true },
} satisfies Meta<typeof CountLabel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const Examples: Story = {
  name: "표기 예시",
  render: () => (
    <div className="flex flex-col items-start gap-2">
      <CountLabel count={12400} label="팔로워" compact />
      <CountLabel count={12400} label="팔로워" />
      <CountLabel count={342} label="포스트" />
      <CountLabel count={8900000} label="조회" compact />
    </div>
  ),
};
