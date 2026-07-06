import type { Meta, StoryObj } from "@storybook/nextjs";
import { VerifiedMark } from "@/components/ui/verified-mark";

const meta = {
  title: "Primitives/VerifiedMark",
  component: VerifiedMark,
  parameters: { layout: "centered" },
  argTypes: {
    size: { control: "inline-radio", options: ["sm", "md"] },
    label: { control: "text" },
  },
  args: { size: "sm", label: "인증됨" },
} satisfies Meta<typeof VerifiedMark>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const Sizes: Story = {
  name: "크기",
  render: () => (
    <div className="flex items-center gap-3">
      <VerifiedMark size="sm" />
      <VerifiedMark size="md" />
    </div>
  ),
};

export const WithName: Story = {
  name: "이름 옆 표기",
  render: () => (
    <span className="inline-flex items-center gap-1 text-title-m text-on-surface">
      크리에이터 이름
      <VerifiedMark size="sm" />
    </span>
  ),
};
