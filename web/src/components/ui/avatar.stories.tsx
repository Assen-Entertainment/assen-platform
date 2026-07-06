import type { Meta, StoryObj } from "@storybook/nextjs";
import { Avatar } from "@/components/ui/avatar";

const meta = {
  title: "Primitives/Avatar",
  component: Avatar,
  parameters: { layout: "centered" },
  argTypes: {
    size: { control: "inline-radio", options: ["sm", "md", "lg", "xl"] },
    verified: { control: "boolean" },
    fallback: { control: "text" },
    tone: { control: "text" },
  },
  args: { fallback: "A", size: "md", verified: false },
} satisfies Meta<typeof Avatar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const Sizes: Story = {
  render: () => (
    <div className="flex items-end gap-3">
      <Avatar fallback="S" size="sm" />
      <Avatar fallback="M" size="md" />
      <Avatar fallback="L" size="lg" />
      <Avatar fallback="X" size="xl" />
    </div>
  ),
};

export const Verified: Story = {
  args: { fallback: "V", size: "lg", verified: true },
};

export const DerivedTone: Story = {
  name: "파생 톤(seed)",
  render: () => (
    <div className="flex items-center gap-3">
      <Avatar fallback="가" tone="creator-illustration" />
      <Avatar fallback="나" tone="creator-music" />
      <Avatar fallback="다" tone="creator-vtuber" />
      <Avatar fallback="라" tone="creator-photo" />
    </div>
  ),
};
