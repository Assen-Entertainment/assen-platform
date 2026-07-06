import type { Meta, StoryObj } from "@storybook/nextjs";
import { Skeleton } from "@/components/ui/skeleton";

const meta = {
  title: "Feedback/Skeleton",
  component: Skeleton,
  parameters: { layout: "centered" },
} satisfies Meta<typeof Skeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Line: Story = {
  render: () => <Skeleton className="h-4 w-48" />,
};

export const CardPlaceholder: Story = {
  name: "카드 로딩",
  render: () => (
    <div className="flex w-64 flex-col gap-3">
      <Skeleton className="h-32 w-full rounded-lg" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
    </div>
  ),
};
