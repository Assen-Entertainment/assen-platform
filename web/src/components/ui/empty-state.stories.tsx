import type { Meta, StoryObj } from "@storybook/nextjs";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { FeedIcon } from "@/lib/icons";

const meta = {
  title: "Feedback/EmptyState",
  component: EmptyState,
  parameters: { layout: "centered" },
  argTypes: {
    title: { control: "text" },
    description: { control: "text" },
  },
  args: {
    title: "아직 콘텐츠가 없어요",
    description: "첫 포스트를 올려 팬들과 소통을 시작해보세요.",
  },
} satisfies Meta<typeof EmptyState>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: (args) => (
    <EmptyState
      {...args}
      icon={<FeedIcon className="size-7" />}
      action={<Button size="sm">새로 만들기</Button>}
    />
  ),
};
