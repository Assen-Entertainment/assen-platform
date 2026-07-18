import type { Meta, StoryObj } from "@storybook/nextjs";
import { TimeLabel } from "@/components/ui/time-label";

const meta = {
  title: "Primitives/TimeLabel",
  component: TimeLabel,
  parameters: { layout: "centered" },
  argTypes: {
    children: { control: "text" },
    dateTime: { control: "text" },
  },
  args: { children: "3시간 전", dateTime: "2026-07-06T18:00:00+09:00" },
} satisfies Meta<typeof TimeLabel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Relative: Story = {
  name: "상대 시각",
};

export const Absolute: Story = {
  name: "절대 시각",
  args: { children: "2026년 7월 6일 오후 6:00", dateTime: "2026-07-06T18:00:00+09:00" },
};
