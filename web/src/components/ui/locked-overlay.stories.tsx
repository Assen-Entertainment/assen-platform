import type { Meta, StoryObj } from "@storybook/nextjs";
import { LockedOverlay } from "@/components/ui/locked-overlay";
import { Button } from "@/components/ui/button";

const meta = {
  title: "Feedback/LockedOverlay",
  component: LockedOverlay,
  parameters: { layout: "centered" },
  argTypes: {
    title: { control: "text" },
    description: { control: "text" },
  },
  args: {
    title: "멤버십 전용 콘텐츠",
    description: "이 포스트는 구독자만 볼 수 있어요.",
  },
  render: (args) => (
    <div className="relative aspect-video w-80 overflow-hidden rounded-lg bg-surface-container-high">
      <div className="flex h-full items-center justify-center text-body-s text-on-surface-variant">
        (잠긴 콘텐츠 미리보기)
      </div>
      <LockedOverlay {...args} cta={<Button size="sm">멤버십 구독</Button>} />
    </div>
  ),
} satisfies Meta<typeof LockedOverlay>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const TitleOnly: Story = {
  name: "제목만",
  args: { description: undefined },
  render: (args) => (
    <div className="relative aspect-video w-80 overflow-hidden rounded-lg bg-surface-container-high">
      <LockedOverlay {...args} />
    </div>
  ),
};
