import type { Meta, StoryObj } from "@storybook/nextjs";
import { ErrorState } from "@/components/ui/error-state";

const meta = {
  title: "Feedback/ErrorState",
  component: ErrorState,
  parameters: { layout: "centered" },
  args: { onRetry: () => {} },
} satisfies Meta<typeof ErrorState>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithoutRetry: Story = {
  name: "재시도 없음",
  args: { onRetry: undefined },
};

export const CustomMessage: Story = {
  name: "커스텀 메시지",
  args: {
    title: "결제에 실패했어요",
    description: "카드 정보를 확인한 뒤 다시 시도해 주세요.",
  },
};
