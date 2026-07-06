import type { Meta, StoryObj } from "@storybook/nextjs";
import { Spinner } from "@/components/ui/spinner";

const meta = {
  title: "Feedback/Spinner",
  component: Spinner,
  parameters: { layout: "centered" },
} satisfies Meta<typeof Spinner>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Sizes: Story = {
  render: () => (
    <div className="flex items-center gap-4 text-primary">
      <Spinner className="size-4" />
      <Spinner className="size-6" />
      <Spinner className="size-10" />
    </div>
  ),
};
