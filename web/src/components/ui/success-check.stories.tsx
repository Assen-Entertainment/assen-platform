import type { Meta, StoryObj } from "@storybook/nextjs";
import { SuccessCheck } from "@/components/ui/success-check";

const meta = {
  title: "Feedback/SuccessCheck",
  component: SuccessCheck,
  parameters: { layout: "centered" },
  argTypes: {
    size: { control: "inline-radio", options: ["md", "lg"] },
    label: { control: "text" },
  },
  args: { size: "lg", label: "완료" },
} satisfies Meta<typeof SuccessCheck>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const InContext: Story = {
  name: "결제 완료 화면",
  render: () => (
    <div className="flex flex-col items-center gap-3 text-center">
      <SuccessCheck label="결제 완료" />
      <p className="text-title-l text-on-surface">결제가 완료되었어요</p>
      <p className="text-body-m text-on-surface-variant">주문 내역은 마이페이지에서 확인할 수 있어요.</p>
    </div>
  ),
};
