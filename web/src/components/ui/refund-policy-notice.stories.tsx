import type { Meta, StoryObj } from "@storybook/nextjs";
import { RefundPolicyNotice } from "@/components/ui/refund-policy-notice";

const meta = {
  title: "Notices/RefundPolicyNotice",
  component: RefundPolicyNotice,
  parameters: { layout: "padded" },
  argTypes: {
    showTrust: { control: "boolean" },
  },
  args: { showTrust: true },
  render: (args) => (
    <div className="w-[28rem] max-w-full">
      <RefundPolicyNotice {...args} />
    </div>
  ),
} satisfies Meta<typeof RefundPolicyNotice>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithoutTrust: Story = {
  name: "신뢰 시그널 숨김",
  args: { showTrust: false },
};
